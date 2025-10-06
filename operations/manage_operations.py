import MetaTrader5 as mt5
from datetime import datetime
from operations.close_operations import close_operation_robust

try:
    from metatrader.metatrader import obtener_mensaje_error
except ImportError:
    def obtener_mensaje_error(codigo_error: int) -> str:
        return f"Error desconocido (código: {codigo_error})"

def close_single_operation(ticket, op_type, logger=None):
    """
    Cierra una operación específica usando el método robusto.
    
    Args:
        ticket: Número de ticket de la operación a cerrar
        op_type: Tipo de operación ('position' o 'order')
        logger: Logger para mostrar mensajes (opcional)
    
    Returns:
        bool: True si la operación se cerró exitosamente, False en caso contrario
    """
    try:
        if not mt5.terminal_info():
            if logger:
                logger.error("No hay conexión con MT5")
            return False
        
        if op_type == 'position':
            # Usar la función robusta para posiciones
            return close_operation_robust(ticket, logger)
        elif op_type == 'order':
            # Para órdenes pendientes, usar la función específica
            return cancel_pending_order(ticket, logger)
        return False
    except Exception as e:
        if logger:
            logger.error(f"Error al cerrar operación {ticket}: {e}")
        return False


def cancel_pending_order(ticket, logger=None):
    """
    Cancela una orden pendiente específica.
    
    Args:
        ticket: Número de ticket de la orden a cancelar
        logger: Logger para mostrar mensajes (opcional)
    
    Returns:
        bool: True si la orden se canceló exitosamente, False en caso contrario
    """
    try:
        order = mt5.orders_get(ticket=ticket)
        if not order:
            if logger:
                logger.error(f"No se encontró la orden con ticket {ticket}")
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
                logger.success(f"[{timestamp}] ✅ Orden cancelada - Ticket: {ticket} | "
                              f"Símbolo: {order.symbol} | Volumen: {order.volume}")
            return True
        else:
            if logger:
                if result:
                    error_traducido = obtener_mensaje_error(result.retcode)
                    error_msg = f"{result.comment} (código: {result.retcode} - {error_traducido})"
                else:
                    error_msg = "Error desconocido"
                logger.error(f"❌ Error al cancelar orden {ticket}: {error_msg}")
            return False

    except Exception as e:
        if logger:
            logger.error(f"Excepción al cancelar orden {ticket}: {e}")
        return False
