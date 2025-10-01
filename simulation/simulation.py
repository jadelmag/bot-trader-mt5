import uuid
import pandas as pd
import sys
import os
import json
import threading
import datetime
from forex.forex_list import ForexStrategies
from operations.close_operations import close_operation_robust
from metatrader.metatrader import obtener_mensaje_error
from simulation.key_list import get_name_for_id

# --- MT5 Integration ---
try:
    import MetaTrader5 as mt5
except ImportError:
    print("MetaTrader5 no está instalado. Las operaciones no se ejecutarán.")
    mt5 = None

# --- Path Setup ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# --- Config Path ---
CONFIG_PATH = os.path.join(PROJECT_ROOT, "strategies", "config.json")

from backtesting.detect_candles import CandleDetector
from backtesting.apply_strategies import StrategyAnalyzer
from custom.custom_strategies import CustomStrategies
from simulation.key_list import get_id_for_name
from loggin.audit_log import audit_logger
from candles.candle_list import CandlePatterns

class Simulation:
    """
    Manages the state of a trading simulation, including account metrics, open trades, and P/L.
    """
    def __init__(self, initial_balance: float, symbol: str, timeframe: str, strategies_config: dict = None, logger=None, on_candle_update_callback=None, debug_mode: bool = False):
        """
        Initializes the simulation with a starting balance.

        Args:
            initial_balance (float): The starting capital for the simulation.
            symbol (str): The financial instrument being traded.
            timeframe (str): The timeframe for candles (e.g., 'M1', 'M5').
            strategies_config (dict, optional): Configuration for candle and forex strategies. Defaults to None.
            logger (BodyLogger, optional): Instance of the logger for UI feedback. Defaults to None.
            on_candle_update_callback (callable, optional): Callback function to notify of real-time candle updates.
            debug_mode (bool): Flag to enable or disable debug logging.
        """
        self.balance = initial_balance
        self.equity = initial_balance
        self.margin = 0.0
        self.free_margin = initial_balance
        self.total_profit = 0.0
        self.total_loss = 0.0
        self.symbol = symbol
        self.timeframe = timeframe
        self.timeframe_delta = self._get_timeframe_delta(timeframe)
        
        self.open_trades = []
        self.trades_in_current_candle = 0
        self.trade_types_in_current_candle = []

        # --- Logger and Configs ---
        self.logger = logger
        self.on_candle_update_callback = on_candle_update_callback
        self.debug_mode = debug_mode
        self.strategies_config = strategies_config if strategies_config is not None else {}
        self.general_config = self._load_general_config()
        # Variables para límite de ganancia diaria
        self.daily_start_balance = initial_balance
        self.current_date = datetime.datetime.now().date()

        # --- Audit Logger ---
        self.audit_logger = audit_logger
        if not self.audit_logger.is_enabled:
            if self.debug_mode:
                self._log("[SIM] Advertencia: AuditLogger no está habilitado")
        else:
            if self.debug_mode:
                self._log(f"[SIM] AuditLogger habilitado. Logs en: {audit_logger.log_file_path}")
            self.audit_logger.log_system_event(f"Inicio simulación {self.symbol} {self.timeframe}")

        # --- Candle and Market Analysis Data ---
        self.candles_df = pd.DataFrame(columns=['time', 'open', 'high', 'low', 'close'])
        self.current_candle = None
        self.ma_fast = None
        self.ma_slow = None
        self.atr = None # Añadir para ATR

        self.tracked_tickets = set()  # Set para trackear tickets abiertos
        self.queue = None # <<<< AÑADIDO PARA EVITAR AttributeError
    
        # --- Inicializar MetaTrader 5 ---
        self._init_mt5()
        self._fetch_initial_candles() # Cargar velas históricas

    def set_debug_mode(self, debug_mode: bool):
        """Permite cambiar el modo debug durante la ejecución."""
        if self.debug_mode != debug_mode:
            self.debug_mode = debug_mode
            if self.logger:
                status = "ACTIVADO" if debug_mode else "DESACTIVADO"

    def _get_timeframe_delta(self, timeframe_str):
        """Converts a timeframe string to a pandas Timedelta."""
        mapping = {
            "M1": pd.Timedelta(minutes=1),
            "M5": pd.Timedelta(minutes=5),
            "M15": pd.Timedelta(minutes=15),
            "M30": pd.Timedelta(minutes=30),
            "H1": pd.Timedelta(hours=1),
            "H4": pd.Timedelta(hours=4),
            "D1": pd.Timedelta(days=1),
        }
        return mapping.get(timeframe_str.upper())

    def _log(self, message, level='info'):
        """Helper para registrar mensajes en la UI si el logger está disponible."""
        if not self.logger:
            print(message) # Fallback a la consola
            return
        
        log_methods = {
            'info': self.logger.log,
            'success': self.logger.success,
            'error': self.logger.error,
            'warn': self.logger.warn
        }
        log_methods.get(level, self.logger.log)(message)

        # Registrar también en el archivo JSONL
        if hasattr(self, 'audit_logger') and self.audit_logger.is_enabled:
            self.audit_logger.log_message(message, level.upper())

    def _init_mt5(self):
        """Inicializa la conexión con MetaTrader 5 si no está activa."""
        if not mt5:
            self._log("[SIM-ERROR] La librería MetaTrader5 no está disponible.", 'error')
            return False

        if not mt5.initialize():
            self._log(f"[SIM-ERROR] No se pudo inicializar MT5: {mt5.last_error()}", 'error')
            return False

        info = mt5.account_info()
        if info:
            self._log(f"[SIM] Conectado a MetaTrader 5. Cuenta: {info.login}, Balance: {info.balance}", 'success')
        else:
            self._log("[SIM-WARN] MT5 inicializado pero no se pudo obtener información de la cuenta.", 'warn')
        return True

    def _fetch_initial_candles(self):
        """Carga un historial inicial de velas para asegurar que los indicadores se puedan calcular."""
        if not mt5 or not mt5.terminal_info():
            self._log("[SIM-WARN] No se pueden cargar velas históricas, MT5 no está conectado.", 'warn')
            return

        timeframe_map = {
            "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15,
            "M30": mt5.TIMEFRAME_M30, "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1
        }
        mt5_timeframe = timeframe_map.get(self.timeframe)
        if mt5_timeframe is None:
            self._log(f"[SIM-ERROR] Timeframe '{self.timeframe}' no es válido para la carga de historial.", 'error')
            return

        try:
            # Cargar las últimas 200 velas para tener datos suficientes para los indicadores
            rates = mt5.copy_rates_from_pos(self.symbol, mt5_timeframe, 0, 200)
            if rates is None or len(rates) == 0:
                self._log(f"[SIM-WARN] No se pudieron obtener velas históricas para {self.symbol}: {mt5.last_error()}", 'warn')
                return

            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df = df[['time', 'open', 'high', 'low', 'close']]
            
            self.candles_df = df
            self._log(f"[SIM] Cargadas {len(df)} velas históricas para {self.symbol} en {self.timeframe}.")

            # Calcular indicadores iniciales
            self._calculate_indicators()

        except Exception as e:
            self._log(f"[SIM-ERROR] Error al cargar las velas iniciales: {e}", 'error')

    def _load_general_config(self):
        """Carga la configuración general desde config.json."""
        if not os.path.exists(CONFIG_PATH):
            return {}
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, TypeError):
            self._log("[SIM-ERROR] El archivo de configuración general 'config.json' está corrupto.", 'error')
            return {}

    def _check_daily_profit_limit(self):
        """Verifica si se ha alcanzado el límite de ganancia diaria."""
        daily_limit = self.general_config.get('daily_profit_limit', 0.0)
        if daily_limit <= 0:
            return True  # Sin límite configurado
        
        # Verificar si cambió el día
        current_date = datetime.datetime.now().date()
        if current_date != self.current_date:
            # Nuevo día, resetear balance inicial
            account_info = mt5.account_info() if mt5 else None
            self.daily_start_balance = account_info.balance if account_info else self.balance
            self.current_date = current_date
            self._log(f"[SIM] Nuevo día detectado. Balance inicial: {self.daily_start_balance:.2f}")
        
        # Obtener balance actual
        account_info = mt5.account_info() if mt5 else None
        current_balance = account_info.balance if account_info else self.balance
        
        # Calcular ganancia del día
        daily_profit = current_balance - self.daily_start_balance
        
        if daily_profit >= daily_limit:
            self._log(f"[SIM-LIMIT] Límite de ganancia diaria alcanzado: {daily_profit:.2f}€ >= {daily_limit:.2f}€. No se abrirán nuevas operaciones.", 'warn')
    
            # Cerrar operaciones con beneficio positivo
            self._close_profitable_positions_on_limit()
    
            return False
        
        return True

    def _close_profitable_positions_on_limit(self):
        """Cierra operaciones con beneficio positivo al alcanzar límite diario."""
        if not mt5 or not mt5.terminal_info():
            return
        
        open_positions = mt5.positions_get(symbol=self.symbol)
        if open_positions is None or len(open_positions) == 0:
            return
        
        for position in open_positions:
            if position.profit > 0:
                trade_type = 'long' if position.type == mt5.POSITION_TYPE_BUY else 'short'
                self._log(f"[SIM-LIMIT] Cerrando operación rentable: #{position.ticket}, P/L: +{position.profit:.2f}€", 'success')
                self.close_trade(position.ticket, position.volume, trade_type, "daily_limit_reached")
            else:
                self._log(f"[SIM-LIMIT] Manteniendo operación con pérdida: #{position.ticket}, P/L: {position.profit:.2f}€", 'info')

    def _check_auto_closed_positions(self):
        """Detecta y registra operaciones cerradas automáticamente por MT5 (SL/TP)."""
        if not mt5 or not mt5.terminal_info() or not hasattr(self, 'tracked_tickets'):
            return
        
        # Obtener tickets actualmente abiertos en MT5
        open_positions = mt5.positions_get(symbol=self.symbol)
        current_tickets = set()
        if open_positions:
            current_tickets = {pos.ticket for pos in open_positions}
        
        # Detectar tickets que fueron cerrados
        closed_tickets = self.tracked_tickets - current_tickets
        
        if closed_tickets:
            # Procesar cada ticket cerrado
            for ticket in closed_tickets:
                # Buscar en el historial de deals
                deals = mt5.history_deals_get(position=ticket)
                if deals and len(deals) >= 2:  # Al menos apertura y cierre
                    close_deal = deals[-1]  # Último deal es el cierre
                    open_deal = deals[0]   # Primer deal es la apertura
                    
                    # Determinar tipo de operación
                    trade_type = 'long' if open_deal.type == mt5.DEAL_TYPE_BUY else 'short'
                    
                    # Determinar razón del cierre
                    reason = "SL/TP automático"
                    if close_deal.comment:
                        if 'sl' in close_deal.comment.lower():
                            reason = "SL"
                        elif 'tp' in close_deal.comment.lower():
                            reason = "TP"
                    
                    # Registrar el cierre
                    self._log(
                        f"[SIM] 🔔 Cierre automático detectado: #{ticket} ({trade_type.upper()}) | "
                        f"Razón: {reason} | P/L: ${close_deal.profit:.2f}",
                        'warn' if close_deal.profit < 0 else 'success'
                    )
                    
                    # Procesar resultado
                    self._process_trade_result(
                        ticket,
                        open_deal.comment or "",
                        trade_type,
                        close_deal.profit,
                        self.balance,
                        close_deal.price
                    )
                    
                    # Registrar en audit log
                    if hasattr(self, 'audit_logger') and self.audit_logger.is_enabled:
                        self.audit_logger.log_trade_close(
                            ticket=ticket,
                            symbol=self.symbol,
                            close_price=close_deal.price,
                            profit=close_deal.profit
                        )
            
            # Actualizar set de tickets trackeados
            self.tracked_tickets = current_tickets

    def on_tick(self, timestamp, price):
        """
        Processes a new market tick, aggregating it into candles.
        """
        if not self.timeframe_delta:
            return

        # Align timestamp to the start of the candle's timeframe interval
        candle_start_time = pd.Timestamp(timestamp).floor(self.timeframe_delta)

        # --- New Candle Detection ---
        if self.current_candle is None or candle_start_time > self.current_candle['time']:
            # Finalize the previous candle if it exists
            if self.current_candle is not None:
                # --- NEW CANDLE FORMED --- 
                self.trades_in_current_candle = 0 # Reset counter for the new candle
                self.trade_types_in_current_candle = [] # Reset trade types for the new candle
                self._log(f"[SIM] 📊 Nueva vela {self.timeframe} a las {candle_start_time.strftime('%H:%M:%S')} | Balance: ${self.balance:.2f}")

                # --- Registro de auditoría ---
                if hasattr(self, 'audit_logger') and self.audit_logger.is_enabled:
                    self.audit_logger.log_system_event(f"[SIM] 📊 Nueva vela {self.timeframe} a las {candle_start_time.strftime('%H:%M:%S')} | Balance: ${self.balance:.2f}")


                new_row = pd.DataFrame([self.current_candle])
                if self.candles_df.empty:
                    self.candles_df = new_row
                else:
                    self.candles_df = pd.concat([self.candles_df, new_row], ignore_index=True)
                # A new candle has been confirmed, run analysis
                self._calculate_indicators()
                # Verificar cierres automáticos por SL/TP
                self._check_auto_closed_positions()
                self._analyze_market_and_execute_strategy()

            # Start a new candle
            self.current_candle = {
                'time': candle_start_time,
                'open': price,
                'high': price,
                'low': price,
                'close': price
            }
        else:
            # Update the current candle
            self.current_candle['high'] = max(self.current_candle['high'], price)
            self.current_candle['low'] = min(self.current_candle['low'], price)
            self.current_candle['close'] = price
            
            # Notificar a la GUI sobre la actualización de la vela en tiempo real
            if self.on_candle_update_callback:
                self.on_candle_update_callback(self.current_candle)

        # Update floating P/L for open trades based on the latest price
        self.update_trades({self.symbol: price})

    def _calculate_indicators(self):
        """Calcula los indicadores técnicos necesarios para las estrategias."""
        if self.candles_df.empty:
            return

        # --- ATR (Average True Range) ---
        # Se necesita para el cálculo dinámico de SL/TP en estrategias de velas
        try:
            high_low = self.candles_df['high'] - self.candles_df['low']
            high_close = (self.candles_df['high'] - self.candles_df['close'].shift()).abs()
            low_close = (self.candles_df['low'] - self.candles_df['close'].shift()).abs()
            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            # Usamos una media móvil simple para el ATR para simplicidad en tiempo real
            atr_value = tr.rolling(window=14).mean().iloc[-1]
            self.atr = atr_value if pd.notna(atr_value) else None
            if self.debug_mode:
                self._log(f"[SIM-DEBUG] ATR calculado: {self.atr}") # <-- Línea corregida
        except Exception as e:
            self.atr = None # Resetear si hay un error
            if self.debug_mode:
                self._log(f"[SIM-DEBUG] No se pudo calcular el ATR: {e}", 'warn')

    def _analyze_market_and_execute_strategy(self):
        """
        Analyzes the market on each new completed candle to make trading decisions.
        """
        # Verificar límite de ganancia diaria
        if not self._check_daily_profit_limit():
            return

        if self.candles_df.empty or not self.strategies_config:
            return

        # --- 0. Comprobación de Límite de Equity (Protección de Capital) ---
        equity_limit = self.general_config.get('money_limit', 0.0)
        if equity_limit > 0:
            account_info = mt5.account_info()
            if account_info and account_info.equity < equity_limit:
                self._log(f"[SIM-PROTECTION] Equity ({account_info.equity:.2f}) está por debajo del límite ({equity_limit:.2f}). No se abrirán nuevas operaciones.", 'warn')
                return

        # Ensure DataFrame has correct column names for analyzers
        analysis_df = self.candles_df.rename(columns={
            'open': 'open', 'high': 'high', 'low': 'low', 'close': 'close'
        })

        # --- 0. Verificar datos de velas ---
        if len(self.candles_df) < 2:
            if self.debug_mode:
                self._log("[SIM-DEBUG] No hay suficientes velas para analizar", 'debug')
            return

        # --- 1. Calcular Indicadores ---
        self._calculate_indicators()

        # --- 1.1. Verificar datos de velas ---
        if self.debug_mode:
            self._log(f"[SIM-DEBUG] Total de velas: {len(self.candles_df)}", 'debug')
        if not analysis_df.empty:
            last_candle = analysis_df.iloc[-1]
            if self.debug_mode:
                self._log(f"[SIM-DEBUG] Última vela - O:{last_candle['open']} H:{last_candle['high']} L:{last_candle['low']} C:{last_candle['close']}", 'debug')

        # --- 2. Obtener señales de mercado ---
        ma_signal = self._get_ma_signal(analysis_df)
        candle_signal, pattern_name = self._get_candle_signal(analysis_df)

        # --- 3. Lógica de Cierre de Operaciones ---
        self._check_for_closing_signals(ma_signal, candle_signal)

        # --- 4. Lógica de Apertura de Operaciones (Forex/Candle) ---
        self._execute_forex_strategies(ma_signal, candle_signal)

        # --- 5. Lógica de Apertura de Estrategias Personalizadas ---
        self._execute_custom_strategies()

    def _execute_forex_strategies(self, ma_signal, candle_signal):
        """Maneja la lógica de apertura para estrategias Forex y de Velas estándar."""
        open_positions = mt5.positions_get(symbol=self.symbol)
        if open_positions is None:
            open_positions = []

        # --- 1. Calcular Slots Disponibles --- 
        # Usamos una lógica unificada de slots, ya que MT5 no distingue la fuente de la operación
        active_slots = len(open_positions)
        max_forex_slots = self.strategies_config.get('slots', {}).get('forex', 1)
        max_candle_slots = self.strategies_config.get('slots', {}).get('candle', 1)
        total_max_slots = max_forex_slots + max_candle_slots

        if active_slots >= total_max_slots:
            if self.debug_mode:
                self._log(f"[SIM-DEBUG] Slots ocupados ({active_slots}/{total_max_slots}). No se abrirán nuevas operaciones.")
            return

        # --- 2. Analizar Estrategias de Velas (Tienen Prioridad) ---
        candle_strategies = self.strategies_config.get('candle_strategies', {})
        selected_candle_patterns = {name: cfg for name, cfg in candle_strategies.items() if cfg.get('selected')}

        if selected_candle_patterns:
            candle_signal, pattern_name = self._get_candle_signal(self.candles_df)
            if candle_signal in ['long', 'short'] and 'candle' not in self.trade_types_in_current_candle:
                self._log(f"[SIM] Señal de VELA '{pattern_name}' -> '{candle_signal.upper()}' detectada. Intentando abrir operación.")
                
                # Cargar configuración específica para este patrón
                pattern_config = self._load_candle_pattern_config(pattern_name)
                sl_pips, tp_pips = self._get_sl_tp_for_candle_pattern(pattern_config)

                if sl_pips > 0:
                    volume = self._calculate_volume(sl_pips=sl_pips)
                    if volume > 0:
                        self.open_trade(
                            trade_type=candle_signal,
                            symbol=self.symbol,
                            volume=volume,
                            sl_pips=sl_pips,
                            tp_pips=tp_pips,
                            strategy_name=f"candle_{pattern_name}"
                        )
                        self.trade_types_in_current_candle.append('candle')
                else:
                    self._log(f"[SIM-WARN] SL para '{pattern_name}' es 0. Operación no abierta.", 'warn')


        forex_strategies = self.strategies_config.get('forex_strategies', {})
        selected_forex_strategies = {name: cfg for name, cfg in forex_strategies.items() if cfg.get('selected')}
        
        if not selected_forex_strategies:
            return

        # Iterar sobre cada estrategia de Forex seleccionada y evaluarla
        df_copy = self.candles_df.copy()

        for strategy_name, params in selected_forex_strategies.items():
            strategy_func = getattr(ForexStrategies, strategy_name, None)
            if not strategy_func:
                continue

            # Llamar a la función de la estrategia directamente
            trade_type = strategy_func(df_copy)

            if trade_type in ['long', 'short'] and 'forex' not in self.trade_types_in_current_candle:
                sl_pips = params.get('stop_loss_pips', 20.0)
                rr_ratio = params.get('rr_ratio', 2.0)
                risk_multiplier = params.get('percent_ratio', 1.0)

                volume = self._calculate_volume(sl_pips=sl_pips, risk_multiplier=risk_multiplier)

                if self.debug_mode:
                    self._log(f"[SIM-DEBUG] Parámetros para Forex: SL Pips={sl_pips}, RR Ratio={rr_ratio}, Volumen Calculado={volume}")

                if volume > 0:
                    self._log(f"[SIM] Señal de FOREX '{strategy_name}' -> '{trade_type.upper()}' detectada. Abriendo operación.")
                    self.open_trade(
                        trade_type=trade_type,
                        symbol=self.symbol,
                        volume=volume,
                        sl_pips=sl_pips,
                        tp_pips=sl_pips * rr_ratio,
                        strategy_name=f"forex_{strategy_name}"
                    )
                    self.trade_types_in_current_candle.append('forex')
                    break # Salir del bucle de estrategias forex

    def _execute_custom_strategies(self):
        """Maneja la lógica de ejecución para estrategias personalizadas."""
        custom_strategies_config = self.strategies_config.get('custom_strategies', {})
        if not custom_strategies_config:
            return

        open_positions = mt5.positions_get(symbol=self.symbol)
        if open_positions is None: open_positions = []
        
        active_slots = len(open_positions)
        max_custom_slots = self.strategies_config.get('slots', {}).get('custom', 0)

        if active_slots >= max_custom_slots:
            return

        for strategy_name, config in custom_strategies_config.items():
            if config.get('selected'):
                if strategy_name == 'run_pico_y_pala':
                    # Para Pico y Pala, el volumen se calcula con un SL nocional para el riesgo
                    # La estrategia en sí no usa SL para el cierre, pero lo necesitamos para el cálculo de riesgo.
                    volume = self._calculate_volume(sl_pips=50.0) 
                    self._log(f"[SIM-DEBUG] Volumen calculado para Pico y Pala: {volume:.4f} lots")
                    if volume > 0:
                        self._log(f"[SIM] Lanzando estrategia personalizada '{strategy_name}' en un nuevo hilo.")
                        # Ejecutar en un hilo para no bloquear la simulación
                        thread = threading.Thread(
                            target=CustomStrategies.run_pico_y_pala, 
                            args=(self, self.symbol, volume, self.logger)
                        )
                        thread.daemon = True # El hilo se cerrará si el programa principal termina
                        thread.start()

    def _get_ma_signal(self, df):
        """Calculates moving averages and returns a 'long', 'short', or 'neutral' signal."""
        if len(df) < 50: # Need enough data for slow MA
            return 'neutral'
        
        fast_ma = df['close'].rolling(window=10).mean().iloc[-1]
        slow_ma = df['close'].rolling(window=50).mean().iloc[-1]
        
        signal = 'neutral'
        if fast_ma > slow_ma:
            signal = 'long'
        elif fast_ma < slow_ma:
            signal = 'short'

        if self.debug_mode:
            self._log(f"[SIM-DEBUG] Señal de Medias Móviles (Forex) evaluada: {signal}")

        return signal

    def _get_candle_signal(self, df):
        """Analyzes the last candle for patterns selected in the strategy config."""
        if df.empty or len(df) < 2:
            if self.debug_mode: 
                self._log("[SIM-DEBUG] No hay suficientes velas para analizar", 'debug')
            return 'neutral', None

        candle_strategies = self.strategies_config.get('candle_strategies', {})
        selected_patterns = [
            name.replace('is_', '') 
            for name, config in candle_strategies.items() 
            if config.get('selected')
        ]

        if not selected_patterns:
            if self.debug_mode: 
                self._log("[SIM-DEBUG] No hay patrones de velas seleccionados en la configuración", 'debug')
            return 'neutral', None

        if self.debug_mode:
            self._log(f"[SIM-DEBUG] Patrones seleccionados: {selected_patterns}")

        # Verificar que tengamos datos suficientes
        last_candle = df.iloc[-1]
        if self.debug_mode:
            self._log(f"[SIM-DEBUG] Última vela: O:{last_candle['open']} H:{last_candle['high']} L:{last_candle['low']} C:{last_candle['close']}")

        last_candle_index = len(df) - 1
        candles_list = df.to_dict('records')

        for pattern_name in selected_patterns:
            pattern_func = getattr(CandlePatterns, f'is_{pattern_name}', None)
            if pattern_func:
                try:
                    signal = pattern_func(candles_list, last_candle_index)
                    if signal in ['long', 'short']:
                        self._log(f"[SIM] Patrón {pattern_name} detectado: {signal}", 'info')
                        return signal, pattern_name
                except Exception as e:
                    self._log(f"[SIM-ERROR] Error al detectar patrón {pattern_name}: {str(e)}", 'error')
        
        return 'neutral', None

    def _get_active_forex_params(self):
        """Encuentra la primera estrategia de forex activa y devuelve sus parámetros."""
        forex_strategies = self.strategies_config.get('forex_strategies', {})
        for name, config in forex_strategies.items():
            if config.get('selected'):
                return {
                    'percent_ratio': config.get('percent_ratio', 1.0),
                    'rr_ratio': config.get('rr_ratio', 2.0),
                    'stop_loss_pips': config.get('stop_loss_pips', 20.0)
                }
        return {'percent_ratio': 1.0, 'rr_ratio': 2.0, 'stop_loss_pips': 20.0}

    def _load_candle_pattern_config(self, pattern_name):
        """Carga la configuración JSON para un patrón de vela específico."""
        config_filename = f"{pattern_name.replace('is_', '')}.json"
        config_path = os.path.join(PROJECT_ROOT, "strategies", config_filename)
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                self._log(f"[SIM-WARN] Error al cargar config para '{pattern_name}': {e}. Usando valores por defecto.", 'warn')
        return {}

    def _get_sl_tp_for_candle_pattern(self, config):
        """Calcula SL y TP en pips para una estrategia de vela, usando ATR si está disponible."""
        use_atr = config.get('use_atr_for_sl_tp', False)
        point = mt5.symbol_info(self.symbol).point

        if use_atr and self.atr is not None and self.atr > 0:
            # --- Lógica basada en ATR ---
            atr_sl_multiplier = config.get('atr_sl_multiplier', 1.5)
            atr_tp_multiplier = config.get('atr_tp_multiplier', 2.0)
            
            sl_pips = (self.atr * atr_sl_multiplier) / point
            tp_pips = (self.atr * atr_tp_multiplier) / point
            self._log(f"[SIM-DEBUG] SL/TP calculado con ATR: SL={sl_pips:.1f} pips, TP={tp_pips:.1f} pips")
            return sl_pips, tp_pips
        else:
            # --- Lógica basada en Pips Fijos (Fallback) ---
            sl_pips = config.get('fixed_sl_pips', 30.0)
            tp_pips = config.get('fixed_tp_pips', 60.0)
            if use_atr: # Si se quería usar ATR pero no se pudo
                self._log("[SIM-WARN] No se pudo usar ATR para SL/TP. Usando pips fijos como fallback.", 'warn')
            return sl_pips, tp_pips

    def _calculate_volume(self, sl_pips: float, risk_multiplier: float = 1.0):
        """Calcula el volumen de la operación basado en el riesgo porcentual del equity."""
        if not mt5 or not mt5.terminal_info():
            return 0.0

        try:
            account_info = mt5.account_info()
            symbol_info = mt5.symbol_info(self.symbol)

            if not account_info or not symbol_info:
                self._log("[SIM-ERROR] No se pudo obtener información de la cuenta o del símbolo para calcular el volumen.", 'error')
                return 0.0

            equity = account_info.equity
            risk_percent_str = self.general_config.get('risk_per_trade_percent', "1.0")
            risk_percent = float(risk_percent_str)
            
            final_risk_percent = risk_percent * risk_multiplier

            money_to_risk = equity * (final_risk_percent / 100.0)

            # sl_in_points = sl_pips 
            # loss_per_lot = sl_in_points * symbol_info.trade_tick_value
            sl_in_points = sl_pips * symbol_info.point
            contract_size = symbol_info.trade_contract_size  # Típicamente 100,000 para Forex
            loss_per_lot = sl_in_points * contract_size

            volume = money_to_risk / loss_per_lot

            volume_step = symbol_info.volume_step
            volume = round(volume / volume_step) * volume_step

            if volume < symbol_info.volume_min:
                self._log(f"[SIM-WARN] Volumen calculado ({volume:.2f}) es menor que el mínimo ({symbol_info.volume_min}). No se abrirá operación.", 'warn')
                return 0.0
            if volume > symbol_info.volume_max:
                volume = symbol_info.volume_max
                self._log(f"[SIM-WARN] Volumen calculado excede el máximo. Se ajustará a {symbol_info.volume_max}.", 'warn')

            return volume

        except Exception as e:
            self._log(f"[SIM-ERROR] Error al calcular el volumen: {str(e)}", 'error')
            return 0.0

    def _check_for_closing_signals(self, ma_signal, candle_signal):
        """Cierra posiciones según el tipo de operación:
        - Trades de velas: solo por señales de velas contrarias o SL/TP
        - Trades forex: por MA o velas contrarias
        """
        if not mt5 or not mt5.terminal_info():
            self._log("[SIM-ERROR] No hay conexión con MT5", 'error')
            return

        open_positions = mt5.positions_get(symbol=self.symbol)
        if open_positions is None:
            self._log("[SIM-ERROR] No se pudieron obtener las posiciones abiertas", 'error')
            return

        if len(open_positions) == 0:
            return

        for position in open_positions:
            # Obtener el precio actual
            current_price = (mt5.symbol_info_tick(self.symbol).bid if position.type == mt5.POSITION_TYPE_BUY 
                            else mt5.symbol_info_tick(self.symbol).ask)

            # Verificar TP y SL
            if position.sl > 0 or position.tp > 0:
                sl_hit = (position.type == mt5.POSITION_TYPE_BUY and current_price <= position.sl) or \
                        (position.type == mt5.POSITION_TYPE_SELL and current_price >= position.sl)
                tp_hit = (position.type == mt5.POSITION_TYPE_BUY and current_price >= position.tp) or \
                        (position.type == mt5.POSITION_TYPE_SELL and current_price <= position.tp)

                if sl_hit or tp_hit:
                    reason = "TP" if tp_hit else "SL"
                    self._log(f"[SIM] {reason} alcanzado para posición #{position.ticket} ({'LONG' if position.type == mt5.POSITION_TYPE_BUY else 'SHORT'}). Precio: {current_price:.5f}", 'warn')
                    self.close_trade(position.ticket, position.volume, 
                                'long' if position.type == mt5.POSITION_TYPE_BUY else 'short')
                    continue

            # Determinar tipo de operación por comentario
            position_comment = position.comment if hasattr(position, 'comment') else ""
            is_candle_trade = "candle" in position_comment.lower() or "key-" in position_comment.lower()
            
            # Lógica diferenciada según tipo
            if is_candle_trade:
                # SOLO cerrar por señal de vela contraria (NO por MA)
                close_long = (position.type == mt5.POSITION_TYPE_BUY and candle_signal == 'short')
                close_short = (position.type == mt5.POSITION_TYPE_SELL and candle_signal == 'long')
                
                if close_long or close_short:
                    self._log(f"[SIM] Señal de VELA contraria. Cerrando trade de velas {'LONG' if position.type == mt5.POSITION_TYPE_BUY else 'SHORT'} #{position.ticket}.")
                    self.close_trade(position.ticket, position.volume, 
                                'long' if position.type == mt5.POSITION_TYPE_BUY else 'short')
            else:
                # Forex: cerrar por MA o velas (lógica original)
                close_long = (position.type == mt5.POSITION_TYPE_BUY and 
                            (ma_signal == 'short' or candle_signal == 'short'))
                close_short = (position.type == mt5.POSITION_TYPE_SELL and 
                            (ma_signal == 'long' or candle_signal == 'long'))

                if close_long or close_short:
                    signal_type = []
                    if position.type == mt5.POSITION_TYPE_BUY and ma_signal == 'short':
                        signal_type.append("MA")
                    if position.type == mt5.POSITION_TYPE_BUY and candle_signal == 'short':
                        signal_type.append("Vela")
                    if position.type == mt5.POSITION_TYPE_SELL and ma_signal == 'long':
                        signal_type.append("MA")
                    if position.type == mt5.POSITION_TYPE_SELL and candle_signal == 'long':
                        signal_type.append("Vela")
                        
                    self._log(f"[SIM] Señal contraria ({' y '.join(signal_type)}). Cerrando FOREX {'LONG' if position.type == mt5.POSITION_TYPE_BUY else 'SHORT'} #{position.ticket}.")
                    self.close_trade(position.ticket, position.volume, 
                                'long' if position.type == mt5.POSITION_TYPE_BUY else 'short')

    def open_trade(self, trade_type: str, symbol: str, volume: float, sl_pips: float = 0, tp_pips: float = 0, strategy_name: str = None):
        """
        Abre una operación en MT5 asegurando la conexión antes de enviar la orden.
        """
        if not self._init_mt5():
            return None

        order_type = mt5.ORDER_TYPE_BUY if trade_type == 'long' else mt5.ORDER_TYPE_SELL
        price = mt5.symbol_info_tick(symbol).ask if trade_type == 'long' else mt5.symbol_info_tick(symbol).bid
        point = mt5.symbol_info(symbol).point
        digits = mt5.symbol_info(symbol).digits

        # SL/TP
        sl, tp = 0.0, 0.0
        if trade_type == 'long':
            if sl_pips > 0: sl = round(price - sl_pips * point, digits)
            if tp_pips > 0: tp = round(price + tp_pips * point, digits)
        else:
            if sl_pips > 0: sl = round(price + sl_pips * point, digits)
            if tp_pips > 0: tp = round(price - tp_pips * point, digits)

       
        id_patron = get_id_for_name(strategy_name)
        comment = f"key-{id_patron}-Bot-Simulation"

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(volume),
            "type": order_type,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": 20,
            "magic": 234000,
            "comment": (comment)[:20],
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_FOK,
        }

        result = mt5.order_send(request)

        if self.debug_mode:
            self._log(f"[SIM-DEBUG] Enviando request: {request}")

        if result is None:
            self._log(f"[SIM-ERROR] mt5.order_send devolvió None. last_error={mt5.last_error()}", 'error')
            return None

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            self._log(f"[SIM-ERROR] order_send falló, retcode={result.retcode} ({obtener_mensaje_error(result.retcode)}), last_error={mt5.last_error()}", 'error')
        else:
            # --- Formateo del mensaje de log personalizado ---
            strategy_type = "DESCONOCIDO"
            strat_name_clean = strategy_name or ""
            if strat_name_clean.startswith("forex_"):
                strategy_type = "FOREX"
                strat_name_clean = strat_name_clean.replace("forex_", "")
            elif strat_name_clean.startswith("candle_"):
                strategy_type = "CANDLE"
                strat_name_clean = strat_name_clean.replace("candle_", "")
            elif strat_name_clean.startswith("custom "):
                strategy_type = "CUSTOM"
                strat_name_clean = strat_name_clean.replace("custom ", "")
            else:
                strategy_type = "DESCONOCIDO"
                strat_name_clean = "DESCONOCIDO"

            # --- Registro de auditoría ---
            if hasattr(self, 'audit_logger') and self.audit_logger.is_enabled:
                self.audit_logger.log_trade_open(
                    symbol=symbol,
                    trade_type=trade_type,
                    volume=volume,
                    price=price,
                    sl=sl,
                    tp=tp,
                    comment=comment
                )

            log_message = (
                f"[SIM] Señal de {strategy_type} '{strat_name_clean}' -> '{trade_type.upper()}': "
                f"{price:.{digits}f} | {volume} | {sl} | {tp}"
            )
            self._log(log_message, 'success')
            self.trades_in_current_candle += 1
            # Añadir ticket al set de tracking
            if hasattr(self, 'tracked_tickets') and result.order:
                self.tracked_tickets.add(result.order)

        return result

    def _calculate_money_risk(self, volume, sl_pips):
        """Calcula el riesgo monetario aproximado de una operación."""
        try:
            symbol_info = mt5.symbol_info(self.symbol)
            if not symbol_info:
                return 0.0
            
            sl_in_points = sl_pips
            loss_per_lot = sl_in_points * symbol_info.trade_tick_value
            return loss_per_lot * volume
        except Exception:
            return 0.0

    def update_trades(self, current_prices: dict):
        """
        Updates the floating profit/loss for all open trades based on current market prices.
        """
        total_floating_pl = 0.0
        for trade in self.open_trades:
            if trade['symbol'] in current_prices:
                current_price = current_prices[trade['symbol']]
                if trade['type'] == 'long':
                    trade['floating_pl'] = (current_price - trade['open_price']) * trade['volume']
                else: # short
                    trade['floating_pl'] = (trade['open_price'] - current_price) * trade['volume']
                
                total_floating_pl += trade['floating_pl']

        self.equity = self.balance + total_floating_pl
        self.free_margin = self.equity - self.margin

    def close_trade(self, position_ticket: int, volume: float, trade_type: str, strategy_context: str = None):
        """Cierra una operación mostrando claramente el resultado."""
        if not self._init_mt5():
            return None

        position_info = mt5.positions_get(ticket=position_ticket)
        if not position_info:
            self._log(f"[SIM] Posición {position_ticket} ya cerrada o no existe", 'info')
            return None
            
        position_info = position_info[0]
        balance_before = self.balance

        # Log de P/L flotante antes de cerrar
        floating_pl = position_info.profit
        self._log(f"[SIM] 🔄 Cerrando #{position_ticket} ({trade_type.upper()}) | P/L flotante: ${floating_pl:.2f} | Balance: ${balance_before:.2f}", 'info')

        # Cerrar operación
        if not close_operation_robust(position_ticket, None, 5):
            self._log(f"[ERROR] No se pudo cerrar {position_ticket}", 'error')
            return None

        # Obtener resultado
        deal = mt5.history_deals_get(position=position_ticket)
        if not deal:
            self._log(f"[ERROR] No se obtuvo resultado de {position_ticket}", 'error')
            return None

        self._process_trade_result(
            position_ticket,  # NUEVO
            position_info.comment, 
            trade_type, 
            deal[-1].profit, 
            balance_before,
            position_info.price_current  # NUEVO
        )

        # --- Registro de auditoría ---
        if hasattr(self, 'audit_logger') and self.audit_logger.is_enabled:
            self.audit_logger.log_trade_close(
                ticket=position_ticket,
                symbol=self.symbol,
                close_price=position_info.price_current,
                profit=deal[-1].profit
            )

        return True

    def _process_trade_result(self, ticket: int, comment: str, trade_type: str, profit: float, balance_before: float, close_price: float):
        """Procesa y muestra el resultado de una operación cerrada."""
        # Calcular porcentaje al inicio
        percent = (abs(profit) / balance_before * 100) if balance_before > 0 else 0

        copy_comment = comment
        
        # Obtener nombre de la estrategia
        strategy_name = "Estrategia"
        if comment:
            if "forex_" in comment:
                strategy_name = "FOREX " + comment.split('_')[1] if '_' in comment else "FOREX"
            elif "candle_" in comment:
                strategy_name = "VELA " + comment.split('_')[1] if '_' in comment else "VELA"
            elif "custom" in comment:
                strategy_name = "CUSTOM " + comment.split(' ', 1)[1] if ' ' in comment else "CUSTOM"

        comment_clean = copy_comment.strip()
        keyIDComment = comment_clean.split('-')[1]
        strategy_type = get_name_for_id(int(keyIDComment))

        # Mostrar resultado
        # Añadir ticket y precio de cierre
        if profit > 0:
            self._log(
                f"[SIM] ✅ CIERRE #{ticket} | {strategy_name} | {strategy_type} | {trade_type.upper()} | "
                f"Precio: {close_price:.5f} | GANANCIA: +${profit:.2f} (+{percent:.2f}%)", 
                'success'
            )
        elif profit < 0:
            self._log(
                f"[SIM] ❌ CIERRE #{ticket} | {strategy_name} | {strategy_type} | {trade_type.upper()} | "
                f"Precio: {close_price:.5f} | PÉRDIDA: -${abs(profit):.2f} (-{percent:.2f}%)", 
                'error'
            )
        else:
            self._log(f"[SIM] {strategy_name} | {strategy_type} | {trade_type.upper()} | SIN CAMBIO", 'info')

        # Actualizar métricas
        self.balance += profit
        if profit > 0:
            self.total_profit += profit
        else:
            self.total_loss += abs(profit)

        # Mostrar resumen
        self._log(
            f"[SIM] Balance: ${self.balance:.2f} | "
            f"Ganancias: ${self.total_profit:.2f} | "
            f"Pérdidas: ${self.total_loss:.2f}", 
            'info'
        )

        # Registrar también en el archivo JSONL el resumen
        if hasattr(self, 'audit_logger') and self.audit_logger.is_enabled:
            # Determinar el texto del resultado
            if profit > 0:
                result_text = f"GANANCIA: +${profit:.2f} (+{percent:.2f}%)"
            elif profit < 0:
                result_text = f"PÉRDIDA: -${abs(profit):.2f} (-{percent:.2f}%)"
            else:
                result_text = "SIN CAMBIO"
            
            self.audit_logger.log_system_event(
                f"Balance: ${self.balance:.2f} | "
                f"{strategy_name} | {strategy_type} | {trade_type.upper()} | "
                f"{result_text} | "
                f"Ganancias: ${self.total_profit:.2f} | "
                f"Pérdidas: ${self.total_loss:.2f}"
            )

    def get_account_summary(self):
        """
        Returns a summary of the current account status from MetaTrader 5.
        """
        if not mt5 or not mt5.terminal_info():
            return {
                "balance": self.balance,
                "equity": self.equity,
                "margin": self.margin,
                "free_margin": self.free_margin,
                "profit": 0,
            }
        
        account_info = mt5.account_info()
        if account_info:
            self.balance = account_info.balance
            self.equity = account_info.equity
            self.margin = account_info.margin
            self.free_margin = account_info.margin_free

            return {
                "balance": account_info.balance,
                "equity": account_info.equity,
                "margin": account_info.margin,
                "free_margin": account_info.margin_free,
                "profit": account_info.profit,
            }
        else:
            return {
                "balance": self.balance,
                "equity": self.equity,
                "margin": self.margin,
                "free_margin": self.free_margin,
                "profit": 0,
            }