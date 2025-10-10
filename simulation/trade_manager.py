import uuid
from operations.close_operations import close_operation_robust
from simulation.key_list import get_name_for_id, get_id_for_name

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None


class TradeManager:
    """Gestiona la apertura y cierre de operaciones."""
    
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
    
    def open_trade(self, trade_type, symbol, volume, sl_pips=0, tp_pips=0, strategy_name=None, pattern_config=None):
        """
        Abre una operación en MT5.
        
        Args:
            trade_type: 'long' o 'short'
            symbol: Símbolo a operar
            volume: Volumen en lotes
            sl_pips: Stop Loss en pips
            tp_pips: Take Profit en pips
            strategy_name: Nombre de la estrategia
            pattern_config: Configuración del patrón
        """
        if not mt5 or not mt5.terminal_info():
            self._log("[TRADE-ERROR] MT5 no está conectado.", 'error')
            return None

        order_type = mt5.ORDER_TYPE_BUY if trade_type == 'long' else mt5.ORDER_TYPE_SELL
        price = mt5.symbol_info_tick(symbol).ask if trade_type == 'long' else mt5.symbol_info_tick(symbol).bid
        point = mt5.symbol_info(symbol).point
        digits = mt5.symbol_info(symbol).digits

        # Aplicar configuración de SL/TP
        sl, tp = 0.0, 0.0
        
        if pattern_config:
            use_sl = pattern_config.get('use_stop_loss', True)
            use_tp = pattern_config.get('use_take_profit', True)
        else:
            use_sl = True
            use_tp = True
        
        if trade_type == 'long':
            if use_sl and sl_pips > 0: 
                sl = round(price - sl_pips * point, digits)
            if use_tp and tp_pips > 0: 
                tp = round(price + tp_pips * point, digits)
        else:
            if use_sl and sl_pips > 0: 
                sl = round(price + sl_pips * point, digits)
            if use_tp and tp_pips > 0: 
                tp = round(price - tp_pips * point, digits)

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

        if self.simulation.debug_mode:
            self._log(f"[TRADE-DEBUG] Enviando request: {request}")

        if result is None:
            self._log(f"[TRADE-ERROR] mt5.order_send devolvió None. last_error={mt5.last_error()}", 'error')
            return None

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            from metatrader.metatrader import obtener_mensaje_error
            self._log(f"[TRADE-ERROR] order_send falló, retcode={result.retcode} ({obtener_mensaje_error(result.retcode)})", 'error')
        else:
            # Formateo del mensaje de log
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

            # Registro de auditoría
            if hasattr(self.simulation, 'audit_logger') and self.simulation.audit_logger.is_enabled:
                self.simulation.audit_logger.log_trade_open(
                    symbol=symbol,
                    trade_type=trade_type,
                    volume=volume,
                    price=price,
                    sl=sl,
                    tp=tp,
                    comment=comment
                )

            log_message = (
                f"[TRADE] Señal de {strategy_type} '{strat_name_clean}' -> '{trade_type.upper()}': "
                f"{price:.{digits}f} | {volume} | {sl} | {tp}"
            )
            self._log(log_message, 'success')
            self.simulation.trades_in_current_candle += 1
            
            # Guardar configuración del patrón
            if pattern_config and result.order:
                self.simulation.candle_pattern_configs[result.order] = {
                    'config': pattern_config,
                    'pattern_name': strategy_name,
                    'entry_price': price,
                    'sl_pips': sl_pips,
                    'tp_pips': tp_pips
                }
            
            # Añadir ticket al tracking
            if hasattr(self.simulation, 'tracked_tickets') and result.order:
                self.simulation.tracked_tickets.add(result.order)
            
            # Guardar SL/TP
            if result.order:
                self.simulation.positions_sl_tp[result.order] = {
                    'sl': sl,
                    'tp': tp,
                    'trade_type': trade_type,
                    'entry_price': price
                }

        return result
    
    def close_trade(self, position_ticket, volume, trade_type, strategy_context=None):
        """Cierra una operación mostrando claramente el resultado."""
        if not mt5 or not mt5.terminal_info():
            return None

        position_info = mt5.positions_get(ticket=position_ticket)
        if not position_info:
            self._log(f"[TRADE] Posición {position_ticket} ya cerrada o no existe", 'info')
            return None
            
        position_info = position_info[0]
        balance_before = self.simulation.balance

        # Log de P/L flotante antes de cerrar
        floating_pl = position_info.profit
        self._log(f"[TRADE] 🔄 Cerrando #{position_ticket} ({trade_type.upper()}) | P/L flotante: ${floating_pl:.2f} | Balance: ${balance_before:.2f}", 'info')

        # Cerrar operación
        if not close_operation_robust(position_ticket, None, 5):
            self._log(f"[TRADE-ERROR] No se pudo cerrar {position_ticket}", 'error')
            return None

        # Obtener resultado
        deal = mt5.history_deals_get(position=position_ticket)
        if not deal:
            self._log(f"[TRADE-ERROR] No se obtuvo resultado de {position_ticket}", 'error')
            return None

        self.process_trade_result(
            position_ticket,
            position_info.comment, 
            trade_type, 
            deal[-1].profit, 
            balance_before,
            position_info.price_current
        )

        # Registro de auditoría
        if hasattr(self.simulation, 'audit_logger') and self.simulation.audit_logger.is_enabled:
            self.simulation.audit_logger.log_trade_close(
                ticket=position_ticket,
                symbol=self.simulation.symbol,
                close_price=position_info.price_current,
                profit=deal[-1].profit
            )

        # Limpiar configuración guardada
        if position_ticket in self.simulation.candle_pattern_configs:
            del self.simulation.candle_pattern_configs[position_ticket]

        if position_ticket in self.simulation.positions_sl_tp:
            del self.simulation.positions_sl_tp[position_ticket]

        return True
    
    def process_trade_result(self, ticket, comment, trade_type, profit, balance_before, close_price):
        """Procesa y muestra el resultado de una operación cerrada."""
        percent = (abs(profit) / balance_before * 100) if balance_before > 0 else 0

        copy_comment = comment
        
        # Obtener nombre de la estrategia
        strategy_name = "Estrategia"
        strategy_type = "Manual"

        comment_clean = copy_comment.strip()
        
        try:
            if comment_clean.startswith('key-') and '-bot-' in comment_clean.lower():
                parts = comment_clean.split('-')
                if len(parts) > 1:
                    keyIDComment = parts[1]
                    strategy_name = get_name_for_id(int(keyIDComment))
             
        except (ValueError, IndexError):
            pass

        if strategy_name:
            if "forex_" in strategy_name:
                strategy_name = "FOREX " + strategy_name.split('_')[1] if '_' in strategy_name else "FOREX"
                strategy_type = "FOREX"
            elif "candle_" in strategy_name:
                strategy_name = "VELA " + strategy_name.split('_')[1] if '_' in strategy_name else "VELA"
                strategy_type = "VELA"
            elif "custom" in strategy_name:
                strategy_name = "CUSTOM " + strategy_name.split(' ', 1)[1] if ' ' in strategy_name else "CUSTOM"
                strategy_type = "CUSTOM"
            else:
                strategy_name = "Estrategia"
                strategy_type = "Manual"
        

        # Mostrar resultado
        if profit > 0:
            self._log(
                f"[TRADE] ✅ CIERRE #{ticket} | {strategy_name} | {strategy_type} | {trade_type.upper()} | "
                f"Precio: {close_price:.5f} | GANANCIA: +${profit:.2f} (+{percent:.2f}%)", 
                'success'
            )
        elif profit < 0:
            self._log(
                f"[TRADE] ❌ CIERRE #{ticket} | {strategy_name} | {strategy_type} | {trade_type.upper()} | "
                f"Precio: {close_price:.5f} | PÉRDIDA: -${abs(profit):.2f} (-{percent:.2f}%)", 
                'error'
            )
        else:
            self._log(f"[TRADE] {strategy_name} | {strategy_type} | {trade_type.upper()} | SIN CAMBIO", 'info')

        # Actualizar métricas
        self.simulation.balance += profit
        if profit > 0:
            self.simulation.total_profit += profit
        else:
            self.simulation.total_loss += abs(profit)

        # Mostrar resumen
        self._log(
            f"[TRADE] Balance: ${self.simulation.balance:.2f} | "
            f"Ganancias: ${self.simulation.total_profit:.2f} | "
            f"Pérdidas: ${self.simulation.total_loss:.2f}", 
            'info'
        )

        # Registrar en audit log
        if hasattr(self.simulation, 'audit_logger') and self.simulation.audit_logger.is_enabled:
            if profit > 0:
                result_text = f"GANANCIA: +${profit:.2f} (+{percent:.2f}%)"
            elif profit < 0:
                result_text = f"PÉRDIDA: -${abs(profit):.2f} (-{percent:.2f}%)"
            else:
                result_text = "SIN CAMBIO"
            
            self.simulation.audit_logger.log_system_event(
                f"Balance: ${self.simulation.balance:.2f} | "
                f"{strategy_name} | {strategy_type} | {trade_type.upper()} | "
                f"{result_text} | "
                f"Ganancias: ${self.simulation.total_profit:.2f} | "
                f"Pérdidas: ${self.simulation.total_loss:.2f}"
            )
    
    def update_trades(self, current_prices):
        """Actualiza el P/L flotante de todas las operaciones abiertas."""
        total_floating_pl = 0.0
        for trade in self.simulation.open_trades:
            if trade['symbol'] in current_prices:
                current_price = current_prices[trade['symbol']]
                if trade['type'] == 'long':
                    trade['floating_pl'] = (current_price - trade['open_price']) * trade['volume']
                else:  # short
                    trade['floating_pl'] = (trade['open_price'] - current_price) * trade['volume']
                
                total_floating_pl += trade['floating_pl']

        self.simulation.equity = self.simulation.balance + total_floating_pl
        self.simulation.free_margin = self.simulation.equity - self.simulation.margin