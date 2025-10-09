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

def execute_manual_trade(trade_data, logger=None):
    """
    Ejecuta una operación manual en MT5.
    
    Args:
        trade_data: Diccionario con los datos de la operación
        logger: Logger para mostrar mensajes (opcional)
    
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        if not mt5.terminal_info():
            return False, "No hay conexión con MT5"
        
        symbol = trade_data['symbol']
        order_type_str = trade_data['order_type']
        volume = trade_data['volume']
        price = trade_data.get('price')
        sl = trade_data.get('sl')
        tp = trade_data.get('tp')
        deviation = trade_data.get('deviation', 20)
        comment = trade_data.get('comment', 'manual_trade')
        magic_number = trade_data.get('magic_number', 123456)
        
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
            "magic": int(magic_number),
            "comment": comment[:25],  # Limitar a 25 caracteres
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
                if logger:
                    logger.error(f"Formato de expiración inválido: {expiration}")
        
        # Intentar con diferentes filling modes
        filling_modes = [mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_RETURN]
        result = None
        
        for filling_mode in filling_modes:
            request["type_filling"] = filling_mode
            result = mt5.order_send(request)
            
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                ticket = result.order
                msg = f"Ticket: {ticket} | Precio: {price:.5f} | Volumen: {volume}"
                if logger:
                    logger.success(f"[MANUAL] {order_type_str.upper()} ejecutado - {msg}")
                return True, msg
            
            # Si el error no es de filling mode, no intentar otros modos
            if result and result.retcode != 10030:  # 10030 = Unsupported filling mode
                break
        
        # Si llegamos aquí, la operación falló
        if result:
            error_traducido = obtener_mensaje_error(result.retcode)
            error_msg = f"{result.comment} (código: {result.retcode} - {error_traducido})"
        else:
            error_msg = "Error desconocido al enviar la orden"
        
        if logger:
            logger.error(f"[MANUAL] Error al ejecutar {order_type_str.upper()}: {error_msg}")
        
        return False, error_msg
        
    except Exception as e:
        error_msg = f"Excepción al ejecutar operación manual: {e}"
        if logger:
            logger.error(error_msg)
        return False, str(e)


