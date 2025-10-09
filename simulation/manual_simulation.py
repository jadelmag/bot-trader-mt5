import MetaTrader5 as mt5
from datetime import datetime
from operations.close_operations import close_operation_robust

class ManualTradeManager:
    """Gestor independiente de operaciones manuales."""
    
    def __init__(self, simulation=None, logger=None):
        """
        Inicializa el gestor de operaciones manuales.
        
        Args:
            simulation: Instancia principal de simulación (para coordinar balance)
            logger: Logger para mensajes
        """
        self.simulation = simulation
        self.logger = logger
        self.manual_tickets = set()  # Conjunto para almacenar tickets de operaciones manuales
        
        # Magic number específico para operaciones manuales
        self.MANUAL_MAGIC = 999999
        
    def _log(self, message, level='info'):
        """Helper para registrar mensajes."""
        if not self.logger:
            return
            
        log_methods = {
            'info': self.logger.log,
            'success': self.logger.success,
            'error': self.logger.error,
            'warn': self.logger.warn
        }
        log_methods.get(level, self.logger.log)(message)
    
    def open_manual_trade(self, trade_data):
        """
        Abre una operación manual.
        
        Args:
            trade_data: Diccionario con los datos de la operación
        
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            if not mt5.terminal_info():
                return False, "No hay conexión con MT5"
            
            # Extraer datos de la operación
            symbol = trade_data['symbol']
            order_type_str = trade_data['order_type']
            volume = trade_data['volume']
            price = trade_data.get('price')
            sl = trade_data.get('sl')
            tp = trade_data.get('tp')
            deviation = trade_data.get('deviation', 20)
            comment = trade_data.get('comment', 'manual')
            
            # Mapear tipo de orden
            order_type_map = {
                'buy': mt5.ORDER_TYPE_BUY,
                'sell': mt5.ORDER_TYPE_SELL,
                'buy_limit': mt5.ORDER_TYPE_BUY_LIMIT,
                'sell_limit': mt5.ORDER_TYPE_SELL_LIMIT,
                'buy_stop': mt5.ORDER_TYPE_BUY_STOP,
                'sell_stop': mt5.ORDER_TYPE_SELL_STOP
            }
            
            order_type = order_type_map.get(order_type_str)
            if order_type is None:
                return False, f"Tipo de orden no válido: {order_type_str}"
            
            # Obtener información del símbolo
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                return False, f"No se pudo obtener información del símbolo {symbol}"
            
            # Obtener precio actual si no se especificó
            if price is None or order_type_str in ('buy', 'sell'):
                tick = mt5.symbol_info_tick(symbol)
                if not tick:
                    return False, "No se pudo obtener el precio actual"
                
                if order_type_str == 'buy':
                    price = tick.ask
                else:
                    price = tick.bid
            
            # Determinar la acción
            if order_type_str in ('buy', 'sell'):
                action = mt5.TRADE_ACTION_DEAL
            else:
                action = mt5.TRADE_ACTION_PENDING
            
            # Construir la solicitud
            request = {
                "action": action,
                "symbol": symbol,
                "volume": float(volume),
                "type": order_type,
                "price": float(price),
                "deviation": int(deviation),
                "magic": self.MANUAL_MAGIC,  # Magic number específico para manuales
                "comment": f"MANUAL-{comment}"[:25],  # Prefijo MANUAL-
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # Añadir SL y TP si se especificaron
            if sl is not None:
                request["sl"] = float(sl)
            if tp is not None:
                request["tp"] = float(tp)
            
            # Añadir expiración para órdenes pendientes
            expiration = trade_data.get('expiration')
            if expiration and order_type_str not in ('buy', 'sell'):
                try:
                    exp_datetime = datetime.strptime(expiration, "%Y-%m-%d %H:%M:%S")
                    request["expiration"] = int(exp_datetime.timestamp())
                    request["type_time"] = mt5.ORDER_TIME_SPECIFIED
                except ValueError:
                    self._log(f"Formato de expiración inválido: {expiration}", 'error')
            
            # Intentar con diferentes filling modes
            filling_modes = [mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_RETURN]
            result = None
            
            for filling_mode in filling_modes:
                request["type_filling"] = filling_mode
                result = mt5.order_send(request)
                
                if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                    ticket = result.order
                    
                    # Añadir a nuestro tracking de tickets manuales
                    self.manual_tickets.add(ticket)
                    
                    msg = f"Ticket: {ticket} | Precio: {price:.5f} | Volumen: {volume}"
                    self._log(f"[MANUAL] {order_type_str.upper()} ejecutado - {msg}", 'success')
                    return True, msg
                
                # Si el error no es de filling mode, no intentar otros modos
                if result and result.retcode != 10030:  # 10030 = Unsupported filling mode
                    break
            
            # Si llegamos aquí, la operación falló
            if result:
                error_msg = f"{result.comment} (código: {result.retcode})"
            else:
                error_msg = "Error desconocido al enviar la orden"
            
            self._log(f"[MANUAL] Error al ejecutar {order_type_str.upper()}: {error_msg}", 'error')
            return False, error_msg
            
        except Exception as e:
            error_msg = f"Excepción al ejecutar operación manual: {e}"
            self._log(error_msg, 'error')
            return False, str(e)
    
    def close_manual_trade(self, ticket):
        """
        Cierra una operación manual específica.
        
        Args:
            ticket: Número de ticket de la operación a cerrar
            
        Returns:
            bool: True si se cerró exitosamente
        """
        try:
            # Verificar si es una posición manual nuestra
            if ticket not in self.manual_tickets:
                self._log(f"La operación {ticket} no es una operación manual registrada", 'error')
                return False
                
            # Intentar cerrar la operación
            success = close_operation_robust(ticket, self.logger)
            
            if success:
                # Remover del tracking si se cerró exitosamente
                self.manual_tickets.remove(ticket)
                
            return success
            
        except Exception as e:
            self._log(f"Error al cerrar operación manual {ticket}: {e}", 'error')
            return False
    
    def update_manual_trades(self):
        """
        Actualiza el estado de las operaciones manuales.
        Verifica si alguna operación manual fue cerrada externamente.
        """
        if not mt5 or not mt5.terminal_info():
            return
            
        # Verificar tickets aún abiertos
        open_positions = mt5.positions_get()
        if open_positions:
            current_tickets = {pos.ticket for pos in open_positions}
            closed_tickets = self.manual_tickets - current_tickets
            
            # Actualizar nuestra lista de tickets
            if closed_tickets:
                for ticket in closed_tickets:
                    self._log(f"Operación manual #{ticket} cerrada externamente", 'info')
                    
                self.manual_tickets -= closed_tickets
    
    def get_manual_trades_count(self):
        """Devuelve el número de operaciones manuales activas."""
        return len(self.manual_tickets)