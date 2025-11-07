import threading
import pandas as pd
from forex.forex_list import ForexStrategies
from custom.custom_strategies import CustomStrategies
from candles.candle_list import CandlePatterns

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None


class SignalAnalyzer:
    """Analiza señales de mercado y ejecuta estrategias."""
    
    def __init__(self, simulation, logger=None):
        self.simulation = simulation
        self.logger = logger
    
    def _log(self, message, level='info'):
        """Helper para registrar mensajes."""
        if self.logger:
            log_methods = {
                'info': self.logger.log,
                'success': self.logger.success,
                'error': self.logger.error,
                'warn': self.logger.warn
            }
            log_methods.get(level, self.logger.log)(message)
        else:
            print(message)
    
    def analyze_market_and_execute_strategy(self):
        """Analiza el mercado en cada vela completada para tomar decisiones de trading."""
        # Verificar límite de ganancia diaria
        if not self.simulation.risk_manager.check_daily_profit_limit():
            return

        if self.simulation.candles_df.empty or not self.simulation.strategies_config:
            return

        # Comprobación de límite de equity
        equity_limit = self.simulation.general_config.get('money_limit', 0.0)
        if equity_limit > 0:
            account_info = mt5.account_info()
            if account_info and account_info.equity < equity_limit:
                self._log(f"[SIGNAL-PROTECTION] Equity ({account_info.equity:.2f}) por debajo del límite ({equity_limit:.2f}).", 'warn')
                return

        analysis_df = self.simulation.candles_df.rename(columns={
            'open': 'open', 'high': 'high', 'low': 'low', 'close': 'close'
        })

        if len(self.simulation.candles_df) < 2:
            if self.simulation.debug_mode:
                self._log("[SIGNAL-DEBUG] No hay suficientes velas para analizar", 'debug')
            return

        # Calcular indicadores
        self.simulation.candles_df = self.simulation.indicator_calculator.calculate_all_indicators(self.simulation.candles_df)

        if self.simulation.debug_mode:
            self._log(f"[SIGNAL-DEBUG] Total de velas: {len(self.simulation.candles_df)}", 'debug')

        # Obtener señales de mercado
        candle_signal, pattern_name = self.get_candle_signal(analysis_df)

        # Lógica de cierre de operaciones
        self.check_for_closing_signals(candle_signal)

        # Aplicar trailing stop
        self.simulation.position_monitor.apply_trailing_stop()

        # Lógica de apertura de operaciones
        self.execute_forex_strategies(candle_signal)

        # Estrategias personalizadas
        self.execute_custom_strategies()
    
    def get_candle_signal(self, df):
        """Analiza la última vela para detectar patrones."""
        if df.empty or len(df) < 2:
            if self.simulation.debug_mode: 
                self._log("[SIGNAL-DEBUG] No hay suficientes velas para analizar", 'debug')
            return 'neutral', None

        candle_strategies = self.simulation.strategies_config.get('candle_strategies', {})
        selected_patterns = [
            name.replace('is_', '') 
            for name, config in candle_strategies.items() 
            if config.get('selected')
        ]

        if not selected_patterns:
            if self.simulation.debug_mode: 
                self._log("[SIGNAL-DEBUG] No hay patrones de velas seleccionados", 'debug')
            return 'neutral', None

        if self.simulation.debug_mode:
            self._log(f"[SIGNAL-DEBUG] Patrones seleccionados: {selected_patterns}")

        last_candle_index = len(df) - 1
        candles_list = df.to_dict('records')

        for pattern_name in selected_patterns:
            pattern_func = getattr(CandlePatterns, f'is_{pattern_name}', None)
            if pattern_func:
                try:
                    signal = pattern_func(candles_list, last_candle_index)
                    if signal in ['long', 'short']:
                        return signal, pattern_name
                except Exception as e:
                    self._log(f"[SIGNAL-ERROR] Error al detectar patrón {pattern_name}: {str(e)}", 'error')
        
        return 'neutral', None
    
    def execute_forex_strategies(self, candle_signal):
        """Maneja la lógica de apertura para estrategias Forex y de Velas."""
        open_positions = mt5.positions_get(symbol=self.simulation.symbol)
        if open_positions is None:
            open_positions = []

        active_slots = len(open_positions)
        max_forex_slots = self.simulation.strategies_config.get('slots', {}).get('forex', 1)
        max_candle_slots = self.simulation.strategies_config.get('slots', {}).get('candle', 1)
        total_max_slots = max_forex_slots + max_candle_slots

        # Verificar si hay slots disponibles para estrategias forex
        if max_forex_slots == 0:
            if self.simulation.debug_mode:
                self._log("[SIGNAL-DEBUG] Slots forex = 0. No se ejecutan estrategias forex.")
            # Solo procesar estrategias de velas si hay slots disponibles
            if max_candle_slots == 0:
                return
            elif active_slots >= max_candle_slots:
                if self.simulation.debug_mode:
                    self._log(f"[SIGNAL-DEBUG] Slots candle ocupados ({active_slots}/{max_candle_slots}).")
                return

        if active_slots >= total_max_slots:
            if self.simulation.debug_mode:
                self._log(f"[SIGNAL-DEBUG] Slots ocupados ({active_slots}/{total_max_slots}).")
            return

        # Analizar estrategias de velas
        if max_candle_slots == 0:
            if self.simulation.debug_mode:
                self._log("[SIGNAL-DEBUG] Slots candle = 0. No se detectan patrones de velas.")
        else:
            candle_strategies = self.simulation.strategies_config.get('candle_strategies', {})
            selected_candle_patterns = {name: cfg for name, cfg in candle_strategies.items() if cfg.get('selected')}

            if selected_candle_patterns:
                candle_signal, pattern_name = self.get_candle_signal(self.simulation.candles_df)
                if candle_signal in ['long', 'short'] and 'candle' not in self.simulation.trade_types_in_current_candle:
                    self._log(f"[SIGNAL] Señal de VELA '{pattern_name}' -> '{candle_signal.upper()}' detectada. Verificando...")
                    
                    # Confirmación con indicadores
                    if not self.simulation.indicator_calculator.confirm_signal_with_indicators(self.simulation.candles_df, candle_signal, pattern_name):
                        if self.simulation.debug_mode:
                            self._log(f"[SIGNAL-DEBUG] Señal de VELA '{pattern_name}' RECHAZADA")
                        return
                    
                    pattern_strategy_config = candle_strategies.get(pattern_name, {})
                    strategy_mode = pattern_strategy_config.get('strategy_mode', 'Default')
                    
                    if strategy_mode == 'Custom':
                        pattern_config = self.simulation.config_loader.load_candle_pattern_config(pattern_name)
                        if self.simulation.debug_mode:
                            self._log(f"[SIGNAL-DEBUG] Usando configuración CUSTOM para '{pattern_name}'")
                    else:
                        pattern_config = {
                            'use_atr_for_sl_tp': False,
                            'fixed_sl_pips': 30.0,
                            'fixed_tp_pips': 60.0,
                            'percent_ratio': 1.0
                        }
                        if self.simulation.debug_mode:
                            self._log(f"[SIGNAL-DEBUG] Usando configuración DEFAULT para '{pattern_name}'")
                    
                    sl_pips, tp_pips = self.simulation.risk_manager.get_sl_tp_for_candle_pattern(pattern_config)
                    risk_multiplier = pattern_config.get('percent_ratio', 1.0)

                    if sl_pips > 0:
                        volume = self.simulation.risk_manager.calculate_volume(
                            risk_multiplier=risk_multiplier,
                            strategy_name=f"candle_{pattern_name}",
                            stop_loss_pips=sl_pips
                        )
                        if volume > 0:
                            self._log(f"[SIGNAL] ✅ Señal de VELA '{pattern_name}' CONFIRMADA. Abriendo {candle_signal.upper()}.")
                            self.simulation.trade_manager.open_trade(
                                trade_type=candle_signal,
                                symbol=self.simulation.symbol,
                                volume=volume,
                                sl_pips=sl_pips,
                                tp_pips=tp_pips,
                                strategy_name=f"candle_{pattern_name}",
                                pattern_config=pattern_config
                            )
                            self.simulation.trade_types_in_current_candle.append('candle')
                    else:
                        self._log(f"[SIGNAL-WARN] SL para '{pattern_name}' es 0. Operación no abierta.", 'warn')

        # Estrategias Forex
        if max_forex_slots == 0:
            if self.simulation.debug_mode:
                self._log("[SIGNAL-DEBUG] Slots forex = 0. No se ejecutan estrategias forex.")
            return

        forex_strategies = self.simulation.strategies_config.get('forex_strategies', {})
        selected_forex_strategies = {name: cfg for name, cfg in forex_strategies.items() if cfg.get('selected')}
        
        if not selected_forex_strategies:
            return

        df_copy = self.simulation.candles_df.copy()

        for strategy_name, params in selected_forex_strategies.items():
            strategy_func = getattr(ForexStrategies, strategy_name, None)
            if not strategy_func:
                continue

            trade_type = strategy_func(df_copy)

            if trade_type in ['long', 'short'] and 'forex' not in self.simulation.trade_types_in_current_candle:
                self._log(f"[SIGNAL] Señal de FOREX '{strategy_name}' -> '{trade_type.upper()}' detectada. Verificando...")
                
                if not self.simulation.indicator_calculator.confirm_signal_with_indicators(self.simulation.candles_df, trade_type, strategy_name):
                    if self.simulation.debug_mode:
                        self._log(f"[SIGNAL-DEBUG] Señal de FOREX '{strategy_name}' RECHAZADA")
                    continue
                
                sl_pips = params.get('stop_loss_pips', 20.0)
                rr_ratio = params.get('rr_ratio', 2.0)
                risk_multiplier = params.get('percent_ratio', 1.0)

                volume = self.simulation.risk_manager.calculate_volume(
                    risk_multiplier=risk_multiplier,
                    strategy_name=strategy_name,
                    stop_loss_pips=sl_pips
                )

                if volume > 0:
                    self._log(f"[SIGNAL] ✅ Señal de FOREX '{strategy_name}' CONFIRMADA. Abriendo {trade_type.upper()}.")
                    self.simulation.trade_manager.open_trade(
                        trade_type=trade_type,
                        symbol=self.simulation.symbol,
                        volume=volume,
                        sl_pips=sl_pips,
                        tp_pips=sl_pips * rr_ratio,
                        strategy_name=f"forex_{strategy_name}"
                    )
                    self.simulation.trade_types_in_current_candle.append('forex')
                    break

    def execute_custom_strategies(self):
        """Maneja la lógica de ejecución para estrategias personalizadas."""
        custom_strategies_config = self.simulation.strategies_config.get('custom_strategies', {})
        if not custom_strategies_config:
            return

        for strategy_name, config in custom_strategies_config.items():
            if config.get('selected'):
                if strategy_name == 'strategy_scalping_m1':
                    volume = self.simulation.risk_manager.calculate_volume(
                        risk_multiplier=1.0,
                        strategy_name=strategy_name,
                        stop_loss_pips=config.get('stop_loss_pips', 10.0)
                    )
                    if volume > 0:
                        self._log(f"[SIGNAL] Lanzando estrategia personalizada '{strategy_name}'.")
                        # Obtener parámetros de configuración o usar valores por defecto
                        entry_pct = config.get('entry_pct', 0.05)
                        exit_pct = config.get('exit_pct', 0.5)
                        n_bars = config.get('n_bars', 60)
                        
                        thread = threading.Thread(
                            target=CustomStrategies.strategy_scalping_m1, 
                            args=(self.simulation.symbol, volume, entry_pct, exit_pct, n_bars, self.logger)
                        )
                        thread.daemon = True
                        thread.start()
    
    def check_for_closing_signals(self, candle_signal):
        """Cierra operaciones según configuración y señales de mercado."""
        if not mt5 or not mt5.terminal_info():
            return
        
        open_positions = mt5.positions_get(symbol=self.simulation.symbol)
        if not open_positions:
            return
        
        for position in open_positions:
            ticket = position.ticket
            
            # Verificar si es una operación de patrón de vela
            if ticket in self.simulation.candle_pattern_configs:
                config_data = self.simulation.candle_pattern_configs[ticket]
                pattern_config = config_data['config']
                pattern_name = config_data['pattern_name']
                trade_type = 'long' if position.type == mt5.POSITION_TYPE_BUY else 'short'
                
                # Verificar use_signal_change
                if pattern_config.get('use_signal_change', False):
                    opposite_signal = 'short' if trade_type == 'long' else 'long'
                    
                    if self.simulation.indicator_calculator.confirm_signal_with_indicators(self.simulation.candles_df, opposite_signal, f"cierre_{pattern_name}"):
                        self._log(
                            f"[SIGNAL] 🔄 Señal contraria confirmada para #{ticket} ({pattern_name}). Cerrando {trade_type.upper()}.",
                            'warn'
                        )
                        self.simulation.trade_manager.close_trade(ticket, position.volume, trade_type, "signal_change")
                        continue
                
                # Verificar use_pattern_reversal
                if pattern_config.get('use_pattern_reversal', False):
                    current_signal, detected_pattern = self.get_candle_signal(self.simulation.candles_df)
                    if detected_pattern:
                        is_reversal = False
                        if trade_type == 'long' and current_signal == 'short':
                            is_reversal = True
                        elif trade_type == 'short' and current_signal == 'long':
                            is_reversal = True
                        
                        if is_reversal:
                            self._log(
                                f"[SIGNAL] 🔄 Patrón de reversión '{detected_pattern}' detectado para #{ticket}. Cerrando {trade_type.upper()}.",
                                'warn'
                            )
                            self.simulation.trade_manager.close_trade(ticket, position.volume, trade_type, f"pattern_reversal_{detected_pattern}")
                            continue
            
            else:
                # Lógica para estrategias Forex
                trade_type = 'long' if position.type == mt5.POSITION_TYPE_BUY else 'short'
                opposite_signal = 'short' if trade_type == 'long' else 'long'
                
                close_position = False
                signal_source = []
                
                if candle_signal == opposite_signal:
                    signal_source.append("Vela")
                    close_position = True
                
                if self.simulation.indicator_calculator.confirm_signal_with_indicators(self.simulation.candles_df, opposite_signal, "cierre_forex"):
                    signal_source.append("Indicadores")
                    close_position = True
                
                if close_position:
                    signal_type_str = " + ".join(signal_source)
                    self._log(
                        f"[SIGNAL] 🔄 Señal contraria ({signal_type_str}) detectada para #{ticket}. Cerrando {trade_type.upper()}.",
                        'warn'
                    )
                    self.simulation.trade_manager.close_trade(ticket, position.volume, trade_type, f"signal_change_{signal_type_str}")