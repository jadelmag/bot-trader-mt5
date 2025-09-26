import MetaTrader5 as mt5
from datetime import datetime

def close_single_operation(ticket, logger=None):
    """
    Cierra una operación específica por su ticket.
    
    Args:
        ticket: Número de ticket de la operación a cerrar
        logger: Logger para mostrar mensajes (opcional)
    
    Returns:
        bool: True si la operación se cerró exitosamente, False en caso contrario
    """
    try:
        # Verificar conexión con MT5
        if not mt5.terminal_info():
            if logger:
                logger.error("No hay conexión con MT5")
            return False
        
        # Obtener información de la posición
        position = mt5.positions_get(ticket=ticket)
        if not position or len(position) == 0:
            if logger:
                logger.error(f"No se encontró la posición con ticket {ticket}")
            return False
        
        position = position[0]  # Tomar la primera (y única) posición
        
        # Determinar el tipo de orden de cierre
        if position.type == mt5.POSITION_TYPE_BUY:
            order_type = mt5.ORDER_TYPE_SELL
            price = mt5.symbol_info_tick(position.symbol).bid
        else:
            order_type = mt5.ORDER_TYPE_BUY
            price = mt5.symbol_info_tick(position.symbol).ask
        
        # Crear la solicitud de cierre
        close_request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": position.symbol,
            "volume": position.volume,
            "type": order_type,
            "position": ticket,
            "price": price,
            "deviation": 20,
            "magic": 0,
            "comment": f"Cerrar operación {ticket}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        # Enviar la orden de cierre
        result = mt5.order_send(close_request)
        
        if result is None:
            if logger:
                logger.error(f"Error al enviar orden de cierre para ticket {ticket}: order_send() falló")
            return False
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            if logger:
                logger.error(f"Error al cerrar operación {ticket}: {result.comment} (código: {result.retcode})")
            return False
        
        # Operación cerrada exitosamente
        profit_loss = position.profit
        trade_type = "Long" if position.type == mt5.POSITION_TYPE_BUY else "Short"
        
        if logger:
            timestamp = datetime.now().strftime("%H:%M:%S")
            logger.log(f"[{timestamp}] Operación cerrada - Ticket: {ticket} | Tipo: {trade_type} | "
                      f"Volumen: {position.volume:.2f} | P/L: {profit_loss:.2f} $ | "
                      f"Precio cierre: {price:.5f}")
        
        return True
        
    except Exception as e:
        if logger:
            logger.error(f"Excepción al cerrar operación {ticket}: {e}")
        return False

def close_all_operations(symbol, logger=None):
    """
    Cierra todas las operaciones abiertas para un símbolo específico.
    
    Args:
        symbol: Símbolo de las operaciones a cerrar
        logger: Logger para mostrar mensajes (opcional)
    
    Returns:
        int: Número de operaciones cerradas exitosamente
    """
    try:
        # Obtener todas las posiciones abiertas para el símbolo
        positions = mt5.positions_get(symbol=symbol)
        
        if not positions or len(positions) == 0:
            if logger:
                logger.log(f"No hay operaciones abiertas para {symbol}")
            return 0
        
        closed_count = 0
        total_profit = 0.0
        
        for position in positions:
            if close_single_operation(position.ticket, logger):
                closed_count += 1
                total_profit += position.profit
        
        if logger and closed_count > 0:
            logger.success(f"Se cerraron {closed_count} operaciones para {symbol}. "
                          f"P/L total: {total_profit:.2f} $")
        
        return closed_count
        
    except Exception as e:
        if logger:
            logger.error(f"Error al cerrar todas las operaciones para {symbol}: {e}")
        return 0