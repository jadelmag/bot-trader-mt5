import uuid
import pandas as pd
import sys
import os
import datetime

# --- Path Setup ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# --- Imports de módulos refactorizados ---
from simulation.config_loader import ConfigLoader
from simulation.indicators import IndicatorCalculator
from simulation.risk_manager import RiskManager
from simulation.position_monitor import PositionMonitor
from simulation.trade_manager import TradeManager
from simulation.signal_analyzer import SignalAnalyzer
from loggin.audit_log import audit_logger

try:
    import MetaTrader5 as mt5
except ImportError:
    print("MetaTrader5 no está instalado. Las operaciones no se ejecutarán.")
    mt5 = None


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
            strategies_config (dict, optional): Configuration for candle and forex strategies.
            logger (BodyLogger, optional): Instance of the logger for UI feedback.
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
        
        # --- Logger and Configs ---
        self.logger = logger
        self.on_candle_update_callback = on_candle_update_callback
        self.debug_mode = debug_mode
        self.strategies_config = strategies_config if strategies_config is not None else {}
        
        # --- Inicializar módulos refactorizados ---
        self.config_loader = ConfigLoader(logger)
        self.general_config = self.config_loader.load_general_config()
        self.timeframe_delta = self.config_loader.get_timeframe_delta(timeframe)
        
        self.indicator_calculator = IndicatorCalculator(debug_mode, logger)
        self.risk_manager = RiskManager(self, logger)
        self.position_monitor = PositionMonitor(self, logger)
        self.trade_manager = TradeManager(self, logger)
        self.signal_analyzer = SignalAnalyzer(self, logger)
        
        # --- Trading State ---
        self.open_trades = []
        self.trades_in_current_candle = 0
        self.trade_types_in_current_candle = []
        self.tracked_tickets = set()
        self.candle_pattern_configs = {}
        self.positions_sl_tp = {}
        self.queue = None
        self.atr = None  # Para trailing stop legacy

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

        # --- Inicializar MetaTrader 5 ---
        self._init_mt5()
        self._fetch_initial_candles()

    def set_debug_mode(self, debug_mode: bool):
        """Permite cambiar el modo debug durante la ejecución."""
        if self.debug_mode != debug_mode:
            self.debug_mode = debug_mode
            self.indicator_calculator.debug_mode = debug_mode
            if self.logger:
                status = "ACTIVADO" if debug_mode else "DESACTIVADO"
                self._log(f"[SIM] Modo Debug {status}")

    def _log(self, message, level='info'):
        """Helper para registrar mensajes en la UI si el logger está disponible."""
        if not self.logger:
            print(message)
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
            self.candles_df = self.indicator_calculator.calculate_all_indicators(self.candles_df)

        except Exception as e:
            self._log(f"[SIM-ERROR] Error al cargar las velas iniciales: {e}", 'error')

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
                self.trades_in_current_candle = 0
                self.trade_types_in_current_candle = []
                self._log(f"[SIM] 📊 Nueva vela {self.timeframe} a las {candle_start_time.strftime('%H:%M:%S')} | Balance: ${self.balance:.2f}")

                # Registro de auditoría
                if hasattr(self, 'audit_logger') and self.audit_logger.is_enabled:
                    self.audit_logger.log_system_event(f"[SIM] 📊 Nueva vela {self.timeframe} a las {candle_start_time.strftime('%H:%M:%S')} | Balance: ${self.balance:.2f}")

                new_row = pd.DataFrame([self.current_candle])
                if self.candles_df.empty:
                    self.candles_df = new_row
                else:
                    self.candles_df = pd.concat([self.candles_df, new_row], ignore_index=True)
                
                # Calcular indicadores
                self.candles_df = self.indicator_calculator.calculate_all_indicators(self.candles_df)
                
                # Verificar cierres automáticos por SL/TP
                self.position_monitor.check_auto_closed_positions()
                
                # Analizar mercado y ejecutar estrategias
                self.signal_analyzer.analyze_market_and_execute_strategy()

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
        self.trade_manager.update_trades({self.symbol: price})

        # Verificar SL/TP en cada tick
        self.position_monitor.check_sl_tp_on_tick(price)

    def open_trade(self, trade_type, symbol, volume, sl_pips=0, tp_pips=0, strategy_name=None, pattern_config=None):
        """Wrapper para abrir operaciones usando TradeManager."""
        return self.trade_manager.open_trade(trade_type, symbol, volume, sl_pips, tp_pips, strategy_name, pattern_config)

    def close_trade(self, position_ticket, volume, trade_type, strategy_context=None):
        """Wrapper para cerrar operaciones usando TradeManager."""
        return self.trade_manager.close_trade(position_ticket, volume, trade_type, strategy_context)

    def _process_trade_result(self, ticket, comment, trade_type, profit, balance_before, close_price):
        """Wrapper para procesar resultados usando TradeManager."""
        return self.trade_manager.process_trade_result(ticket, comment, trade_type, profit, balance_before, close_price)

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