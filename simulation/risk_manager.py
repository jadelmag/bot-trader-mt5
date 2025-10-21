import datetime
import pandas as pd
import math

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None


class RiskManager:
    """Gestiona el riesgo y cálculo de volúmenes."""
    
    def __init__(self, simulation, logger=None):
        self.simulation = simulation
        self.logger = logger
        self.daily_start_balance = simulation.balance
        self.current_date = datetime.datetime.now().date()
    
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

    def calculate_volume(self, risk_multiplier=1.0, strategy_name=None, stop_loss_pips=None):
        """
        Calcula el volumen de la operación basado en el riesgo porcentual, Stop Loss y configuración de estrategia.
        
        Fórmula: Volumen = (Capital × Risk% × Strategy_Ratio%) ÷ (SL_pips × Pip_value)
        
        Args:
            risk_multiplier (float): Multiplicador de riesgo adicional
            strategy_name (str): Nombre de la estrategia para obtener percent_ratio
            stop_loss_pips (float): Stop Loss en pips para calcular el riesgo real
        
        Returns:
            float: Volumen calculado en lotes
        """
        if not mt5 or not mt5.terminal_info():
            self._log("[RISK-ERROR] MT5 no disponible para calcular volumen.", 'error')
            return 0.01  # Volumen mínimo seguro
        
        try:
            account_info = mt5.account_info()
            symbol_info = mt5.symbol_info(self.simulation.symbol)
            
            if not account_info or not symbol_info:
                self._log("[RISK-ERROR] No se pudo obtener información de la cuenta o del símbolo.", 'error')
                return 0.01  # Volumen mínimo seguro
            
            # --- 1. OBTENER CONFIGURACIÓN ---
            equity = account_info.equity
            risk_per_trade_percent = float(self.simulation.general_config.get('risk_per_trade_percent', 1.0))
            
            # Obtener percent_ratio de la estrategia específica
            strategy_config = {}
            if strategy_name and hasattr(self.simulation, 'strategies_config'):
                strategy_config = self.simulation.strategies_config.get(strategy_name, {})
            
            percent_ratio = strategy_config.get('percent_ratio', 1.0)
            
            # Si no se proporciona SL, usar el de la estrategia o default
            if stop_loss_pips is None:
                stop_loss_pips = strategy_config.get('stop_loss_pips', 10.0)
            
            # --- 2. CALCULAR RIESGO EN DINERO ---
            # Riesgo base del capital
            base_risk_amount = equity * (risk_per_trade_percent / 100.0)
            
            # Aplicar ratio de la estrategia
            strategy_risk_amount = base_risk_amount * percent_ratio
            
            # Aplicar multiplicador adicional
            total_risk_amount = strategy_risk_amount * risk_multiplier
            
            # --- 3. CALCULAR VALOR DEL PIP ---
            # Para EURUSD: 1 lote = 10€/pip, 0.1 lote = 1€/pip, 0.01 lote = 0.1€/pip
            contract_size = symbol_info.trade_contract_size  # Normalmente 100,000
            point = symbol_info.point  # Normalmente 0.00001 para EURUSD
            
            # Calcular valor del pip por lote
            if self.simulation.symbol == "EURUSD":
                pip_value_per_lot = 10.0  # 10€ por pip por lote estándar
            else:
                # Cálculo genérico para otros pares
                pip_value_per_lot = (contract_size * point * 10)  # 10 pips = 1 pip real
            
            # --- 4. CALCULAR VOLUMEN BASADO EN SL ---
            if stop_loss_pips > 0 and pip_value_per_lot > 0:
                # Volumen = Riesgo_en_dinero ÷ (SL_pips × Valor_pip_por_lote)
                calculated_volume = total_risk_amount / (stop_loss_pips * pip_value_per_lot)
            else:
                self._log("[RISK-WARN] SL o pip_value inválidos. Usando volumen mínimo.", 'warn')
                calculated_volume = 0.01
            
            # --- 5. APLICAR LÍMITES DEL BROKER ---
            volume_min = symbol_info.volume_min
            volume_max = symbol_info.volume_max
            volume_step = symbol_info.volume_step
            
            # Ajustar a límites
            if calculated_volume < volume_min:
                self._log(f"[RISK-WARN] Volumen calculado ({calculated_volume:.6f}) menor que mínimo ({volume_min}). Ajustado.", 'warn')
                calculated_volume = volume_min
            elif calculated_volume > volume_max:
                self._log(f"[RISK-WARN] Volumen calculado ({calculated_volume:.6f}) mayor que máximo ({volume_max}). Ajustado.", 'warn')
                calculated_volume = volume_max
            
            # Ajustar al step del broker
            if volume_step > 0:
                calculated_volume = round(calculated_volume / volume_step) * volume_step
            
            # --- 6. LOGGING DETALLADO ---
            if self.simulation.debug_mode:
                actual_risk = calculated_volume * stop_loss_pips * pip_value_per_lot
                risk_percentage = (actual_risk / equity) * 100
                
                self._log(
                    f"[RISK-DEBUG] Cálculo de volumen para {strategy_name or 'estrategia'}:\n"
                    f"  Capital: {equity:.2f}€\n"
                    f"  Risk config: {risk_per_trade_percent}%\n"
                    f"  Strategy ratio: {percent_ratio}\n"
                    f"  Risk multiplier: {risk_multiplier}\n"
                    f"  Stop Loss: {stop_loss_pips} pips\n"
                    f"  Pip value: {pip_value_per_lot}€/pip/lote\n"
                    f"  Riesgo objetivo: {total_risk_amount:.2f}€\n"
                    f"  Volumen calculado: {calculated_volume} lotes\n"
                    f"  Riesgo real: {actual_risk}€ ({risk_percentage}%)"
                )
            
            return round(calculated_volume, 6)
            
        except Exception as e:
            self._log(f"[RISK-ERROR] Error al calcular el volumen: {str(e)}", 'error')
            import traceback
            if hasattr(self.simulation, 'debug_mode') and self.simulation.debug_mode:
                self._log(f"[RISK-DEBUG] Traceback: {traceback.format_exc()}", 'error')
            return 0.01  # Volumen mínimo seguro en caso de error

    def check_daily_profit_limit(self):
        """Verifica si se ha alcanzado el límite de ganancia diaria."""
        daily_limit = self.simulation.general_config.get('daily_profit_limit', 0.0)
        if daily_limit <= 0:
            return True  # Sin límite configurado
        
        # Verificar si cambió el día
        current_date = datetime.datetime.now().date()
        if current_date != self.current_date:
            # Nuevo día, resetear balance inicial
            account_info = mt5.account_info() if mt5 else None
            self.daily_start_balance = account_info.balance if account_info else self.simulation.balance
            self.current_date = current_date
            self._log(f"[RISK] Nuevo día detectado. Balance inicial: {self.daily_start_balance:.2f}")
        
        # Obtener balance actual
        account_info = mt5.account_info() if mt5 else None
        current_balance = account_info.balance if account_info else self.simulation.balance
        
        # Calcular ganancia del día
        daily_profit = current_balance - self.daily_start_balance
        
        if daily_profit >= daily_limit:
            self._log(f"[RISK-LIMIT] Límite de ganancia diaria alcanzado: {daily_profit:.2f}€ >= {daily_limit:.2f}€.", 'warn')
            self.close_profitable_positions_on_limit()
            return False
        
        return True
    
    def close_profitable_positions_on_limit(self):
        """Cierra operaciones con beneficio positivo al alcanzar límite diario."""
        if not mt5 or not mt5.terminal_info():
            return
        
        open_positions = mt5.positions_get(symbol=self.simulation.symbol)
        if open_positions is None or len(open_positions) == 0:
            return
        
        for position in open_positions:
            if position.profit > 0:
                trade_type = 'long' if position.type == mt5.POSITION_TYPE_BUY else 'short'
                self._log(f"[RISK-LIMIT] Cerrando operación rentable: #{position.ticket}, P/L: +{position.profit:.2f}€", 'success')
                self.simulation.close_trade(position.ticket, position.volume, trade_type, "daily_limit_reached")
            else:
                self._log(f"[RISK-LIMIT] Manteniendo operación con pérdida: #{position.ticket}, P/L: {position.profit:.2f}€", 'info')
    
    def get_sl_tp_for_candle_pattern(self, config):
        """Calcula SL y TP en pips para una estrategia de vela, usando ATR del DataFrame."""
        use_atr = config.get('use_atr_for_sl_tp', False)
        point = mt5.symbol_info(self.simulation.symbol).point
        
        if use_atr and not self.simulation.candles_df.empty:
            atr_value = self.simulation.candles_df['ATR'].iloc[-1] if 'ATR' in self.simulation.candles_df.columns else None
            
            if atr_value is not None and not pd.isna(atr_value) and atr_value > 0:
                atr_sl_multiplier = config.get('atr_sl_multiplier', 1.5)
                atr_tp_multiplier = config.get('atr_tp_multiplier', 2.0)
                
                sl_pips = (atr_value * atr_sl_multiplier) / point
                tp_pips = (atr_value * atr_tp_multiplier) / point
                
                if self.simulation.debug_mode:
                    self._log(f"[RISK-DEBUG] SL/TP con ATR: ATR={atr_value:.5f}, SL={sl_pips:.1f} pips, TP={tp_pips:.1f} pips")
                
                return sl_pips, tp_pips
            else:
                if self.simulation.debug_mode:
                    self._log("[RISK-DEBUG] ATR no disponible. Usando pips fijos.", 'warn')
        
        # Fallback a pips fijos
        sl_pips = config.get('fixed_sl_pips', 30.0)
        tp_pips = config.get('fixed_tp_pips', 60.0)
        
        return sl_pips, tp_pips
    
    def calculate_money_risk(self, volume, sl_pips):
        """Calcula el riesgo monetario aproximado de una operación."""
        try:
            symbol_info = mt5.symbol_info(self.simulation.symbol)
            if not symbol_info:
                return 0.0
            
            sl_in_points = sl_pips * symbol_info.point
            contract_size = symbol_info.trade_contract_size
            loss_per_lot = sl_in_points * contract_size
            return loss_per_lot * volume
        except Exception:
            return 0.0

