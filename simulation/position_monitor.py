try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None


class PositionMonitor:
    """Monitorea posiciones abiertas para SL/TP automático y trailing stop."""
    
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
    
    def check_close_candle_limit(self):
        """
        Verifica si algún patrón de vela ha alcanzado el límite de P/L para cierre automático
        configurado en close_candle_limit. Solo afecta a patrones de vela, no a estrategias forex.
        """
        if not mt5 or not mt5.terminal_info():
            return
        
        # Obtener el límite configurado de close_candle_limit
        close_candle_limit = self.simulation.general_config.get('close_candle_limit', 0.0)
        if close_candle_limit <= 0:
            return  # Sin límite configurado
            
        open_positions = mt5.positions_get(symbol=self.simulation.symbol)
        if not open_positions:
            return
            
        for position in open_positions:
            ticket = position.ticket
            
            # Solo aplicar a patrones de vela (verificando si están en candle_pattern_configs)
            if ticket not in self.simulation.candle_pattern_configs:
                continue
                
            profit = position.profit
            
            # Si la ganancia de la operación alcanza o supera el límite configurado
            if profit >= close_candle_limit:
                trade_type = 'long' if position.type == mt5.POSITION_TYPE_BUY else 'short'
                
                # Obtener el nombre del patrón de vela
                pattern_name = "desconocido"
                if ticket in self.simulation.candle_pattern_configs:
                    pattern_name = self.simulation.candle_pattern_configs[ticket].get('pattern_name', 'desconocido')
                    
                self._log(
                    f"[MONITOR] 💰 Límite de ganancia en patrón '{pattern_name}': #{ticket} ({trade_type.upper()}) | "
                    f"P/L: ${profit:.2f} >= ${close_candle_limit:.2f}",
                    'success'
                )
                
                # Cerrar la operación
                self.simulation.close_trade(ticket, position.volume, trade_type, "candle_profit_limit_reached")

    def check_auto_closed_positions(self):
        """Detecta y registra operaciones cerradas automáticamente por MT5 (SL/TP)."""
        if not mt5 or not mt5.terminal_info() or not hasattr(self.simulation, 'tracked_tickets'):
            return
        
        # Obtener tickets actualmente abiertos en MT5
        open_positions = mt5.positions_get(symbol=self.simulation.symbol)
        current_tickets = set()
        if open_positions:
            current_tickets = {pos.ticket for pos in open_positions}
        
        # Detectar tickets que fueron cerrados
        closed_tickets = self.simulation.tracked_tickets - current_tickets
        
        if closed_tickets:
            for ticket in closed_tickets:
                deals = mt5.history_deals_get(position=ticket)
                if deals and len(deals) >= 2:
                    close_deal = deals[-1]
                    open_deal = deals[0]
                    
                    trade_type = 'long' if open_deal.type == mt5.DEAL_TYPE_BUY else 'short'
                    
                    reason = "SL/TP automático"
                    if close_deal.comment:
                        if 'sl' in close_deal.comment.lower():
                            reason = "SL"
                        elif 'tp' in close_deal.comment.lower():
                            reason = "TP"
                    
                    self._log(
                        f"[MONITOR] 🔔 Cierre automático detectado: #{ticket} ({trade_type.upper()}) | "
                        f"Razón: {reason} | P/L: ${close_deal.profit:.2f}",
                        'warn' if close_deal.profit < 0 else 'success'
                    )
                    
                    self.simulation._process_trade_result(
                        ticket,
                        open_deal.comment or "",
                        trade_type,
                        close_deal.profit,
                        self.simulation.balance,
                        close_deal.price
                    )
                    
                    if hasattr(self.simulation, 'audit_logger') and self.simulation.audit_logger.is_enabled:
                        self.simulation.audit_logger.log_trade_close(
                            ticket=ticket,
                            symbol=self.simulation.symbol,
                            close_price=close_deal.price,
                            profit=close_deal.profit
                        )
            
            self.simulation.tracked_tickets = current_tickets
    
    def check_sl_tp_on_tick(self, current_price):
        """Verifica si alguna posición ha alcanzado SL o TP en el tick actual."""
        if not mt5 or not mt5.terminal_info():
            return
        
        open_positions = mt5.positions_get(symbol=self.simulation.symbol)
        if not open_positions:
            return
        
        for position in open_positions:
            ticket = position.ticket
            sl = position.sl
            tp = position.tp
            
            if sl == 0 and tp == 0:
                continue
            
            trade_type = 'long' if position.type == mt5.POSITION_TYPE_BUY else 'short'
            should_close = False
            reason = ""
            
            if trade_type == 'long':
                if sl > 0 and current_price <= sl:
                    should_close = True
                    reason = "SL"
                elif tp > 0 and current_price >= tp:
                    should_close = True
                    reason = "TP"
            else:  # short
                if sl > 0 and current_price >= sl:
                    should_close = True
                    reason = "SL"
                elif tp > 0 and current_price <= tp:
                    should_close = True
                    reason = "TP"
            
            if should_close:
                if self.simulation.debug_mode:
                    self._log(f"[MONITOR-DEBUG] {reason} alcanzado para #{ticket} | Precio: {current_price:.5f}")
                
                self._log(f"[MONITOR] 🎯 {reason} alcanzado: #{ticket} ({trade_type.upper()})", 'warn' if reason == 'SL' else 'success')
                self.simulation.close_trade(ticket, position.volume, trade_type, f"{reason}_reached")
    
    def apply_trailing_stop(self):
        """Aplica trailing stop a operaciones que lo tengan configurado."""
        if not mt5 or not mt5.terminal_info():
            return
        
        open_positions = mt5.positions_get(symbol=self.simulation.symbol)
        if not open_positions:
            return
        
        point = mt5.symbol_info(self.simulation.symbol).point
        digits = mt5.symbol_info(self.simulation.symbol).digits
        
        for position in open_positions:
            ticket = position.ticket
            
            if ticket not in self.simulation.candle_pattern_configs:
                continue
            
            config_data = self.simulation.candle_pattern_configs[ticket]
            pattern_config = config_data['config']
            
            if not pattern_config.get('use_trailing_stop', False):
                continue
            
            if self.simulation.atr is None or self.simulation.atr <= 0:
                continue
            
            atr_trailing_multiplier = pattern_config.get('atr_trailing_multiplier', 1.5)
            trailing_distance_pips = (self.simulation.atr * atr_trailing_multiplier) / point
            
            current_price = mt5.symbol_info_tick(self.simulation.symbol).bid if position.type == mt5.POSITION_TYPE_BUY else mt5.symbol_info_tick(self.simulation.symbol).ask
            
            if position.type == mt5.POSITION_TYPE_BUY:
                new_sl = round(current_price - trailing_distance_pips * point, digits)
                if new_sl > position.sl and new_sl < current_price:
                    self.modify_position_sl(ticket, new_sl)
                    if self.simulation.debug_mode:
                        self._log(f"[MONITOR-DEBUG] Trailing Stop aplicado a #{ticket}: nuevo SL={new_sl:.{digits}f}")
            else:
                new_sl = round(current_price + trailing_distance_pips * point, digits)
                if (position.sl == 0 or new_sl < position.sl) and new_sl > current_price:
                    self.modify_position_sl(ticket, new_sl)
                    if self.simulation.debug_mode:
                        self._log(f"[MONITOR-DEBUG] Trailing Stop aplicado a #{ticket}: nuevo SL={new_sl:.{digits}f}")
    
    def modify_position_sl(self, ticket, new_sl):
        """Modifica el SL de una posición existente."""
        position = None
        positions = mt5.positions_get(ticket=ticket)
        if positions and len(positions) > 0:
            position = positions[0]
        
        if not position:
            return False
        
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": position.symbol,
            "position": ticket,
            "sl": new_sl,
            "tp": position.tp,
        }
        
        result = mt5.order_send(request)
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            return True
        else:
            if self.simulation.debug_mode:
                self._log(f"[MONITOR-DEBUG] Error al modificar SL de #{ticket}: {result.retcode if result else 'None'}", 'warn')
            return False