import MetaTrader5 as mt5
from datetime import datetime

def close_single_operation(ticket, op_type, logger=None):
    try:
        if not mt5.terminal_info():
            if logger:
                logger.error("No hay conexión con MT5")
            return False
        
        if op_type == 'position':
            return _close_position(ticket, logger)
        elif op_type == 'order':
            return cancel_pending_order(ticket, logger)
        return False
    except Exception as e:
        if logger:
            logger.error(f"Error al cerrar operación {ticket}: {e}")
        return False

def _close_position(ticket, logger=None):
    try:
        position = mt5.positions_get(ticket=ticket)
        if not position:
            return False
        
        position = position[0]
        
        if position.type == mt5.POSITION_TYPE_BUY:
            order_type = mt5.ORDER_TYPE_SELL
            price = mt5.symbol_info_tick(position.symbol).bid
        else:
            order_type = mt5.ORDER_TYPE_BUY
            price = mt5.symbol_info_tick(position.symbol).ask
        
        close_request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": position.symbol,
            "volume": position.volume,
            "type": order_type,
            "position": ticket,
            "price": price,
            "deviation": 20,
            "magic": 0,
            "comment": f"Cerrar posición {ticket}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_FOK,
        }
        
        result = mt5.order_send(close_request)
        
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            if logger:
                timestamp = datetime.now().strftime("%H:%M:%S")
                trade_type = "Long" if position.type == mt5.POSITION_TYPE_BUY else "Short"
                logger.log(f"[{timestamp}] Posición cerrada - Ticket: {ticket} | Tipo: {trade_type} | "
                          f"Volumen: {position.volume:.2f} | P/L: {position.profit:.2f} $ | "
                          f"Precio cierre: {price:.5f}")
            return True
        return False
    except Exception as e:
        if logger:
            logger.error(f"Error al cerrar posición {ticket}: {e}")
        return False

def cancel_pending_order(ticket, logger=None):
    try:
        order = mt5.orders_get(ticket=ticket)
        if not order:
            return False
        
        order = order[0]
        
        cancel_request = {
            "action": mt5.TRADE_ACTION_REMOVE,
            "order": ticket,
            "comment": f"Cancelar orden {ticket}",
        }
        
        result = mt5.order_send(cancel_request)
        
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            if logger:
                timestamp = datetime.now().strftime("%H:%M:%S")
                logger.log(f"[{timestamp}] Orden cancelada - Ticket: {ticket} | "
                          f"Símbolo: {order.symbol} | Volumen: {order.volume:.2f}")
            return True
        return False
    except Exception as e:
        if logger:
            logger.error(f"Error al cancelar orden {ticket}: {e}")
        return False
    """Abre diálogo para modificar una orden pendiente."""
    try:
        # Obtener información de la orden
        order = mt5.orders_get(ticket=ticket)
        if not order or len(order) == 0:
            if logger:
                logger.error(f"No se encontró la orden con ticket {ticket}")
            return
        
        order = order[0]
        
        # Crear ventana de diálogo
        dialog = tk.Toplevel