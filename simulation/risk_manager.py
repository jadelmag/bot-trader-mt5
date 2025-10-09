import datetime
import pandas as pd

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
    
    def calculate_volume(self, risk_multiplier=1.0):
        """Calcula el volumen de la operación basado en el riesgo porcentual del equity."""
        if not mt5 or not mt5.terminal_info():
            return 0.0

        try:
            account_info = mt5.account_info()
            symbol_info = mt5.symbol_info(self.simulation.symbol)

            if not account_info or not symbol_info:
                self._log("[RISK-ERROR] No se pudo obtener información de la cuenta o del símbolo.", 'error')
                return 0.0

            risk_per_trade_percent = float(self.simulation.general_config.get('risk_per_trade_percent', 1.0))
            volume = risk_per_trade_percent * (risk_multiplier / 100.0)

            if volume < symbol_info.volume_min:
                self._log(f"[RISK-WARN] Volumen calculado ({volume}) es menor que el mínimo ({symbol_info.volume_min}).", 'warn')
                return 0.0
            if volume > symbol_info.volume_max:
                volume = symbol_info.volume_max
                self._log(f"[RISK-WARN] Volumen ajustado al máximo: {symbol_info.volume_max}.", 'warn')

            return volume

        except Exception as e:
            self._log(f"[RISK-ERROR] Error al calcular el volumen: {str(e)}", 'error')
            return 0.0
    
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