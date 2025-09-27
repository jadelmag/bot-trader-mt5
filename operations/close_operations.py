import MetaTrader5 as mt5
from datetime import datetime
import time

def close_single_operation(ticket, logger=None):
    """
    Función de compatibilidad que usa el método robusto.
    Mantiene la interfaz existente para no romper el código actual.
    
    Args:
        ticket: Número de ticket de la operación a cerrar
        logger: Logger para mostrar mensajes (opcional)
    
    Returns:
        bool: True si la operación se cerró exitosamente, False en caso contrario
    """
    return close_operation_robust(ticket, logger)

def close_all_operations(symbol, logger=None):
    """
    Cierra todas las operaciones abiertas para un símbolo específico usando el método robusto.
    
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
        
        if logger:
            logger.log(f"Cerrando {len(positions)} operaciones para {symbol} con método robusto...")
        
        for position in positions:
            if close_operation_robust(position.ticket, logger):
                closed_count += 1
                total_profit += position.profit
        
        if logger and closed_count > 0:
            logger.success(f"✅ Se cerraron {closed_count}/{len(positions)} operaciones para {symbol}. "
                          f"P/L total: {total_profit:.2f} $")
        elif logger:
            logger.error(f"❌ No se pudo cerrar ninguna operación para {symbol}")
        
        return closed_count
        
    except Exception as e:
        if logger:
            logger.error(f"Error al cerrar todas las operaciones para {symbol}: {e}")
        return 0

def close_operation_robust(ticket, logger=None, max_attempts=5):
    """
    Cierra una operación específica por su ticket de forma robusta.
    Intenta cerrar con diferentes filling modes hasta 5 veces cada uno.
    
    Args:
        ticket: Número de ticket de la operación a cerrar
        logger: Logger para mostrar mensajes (opcional)
        max_attempts: Número máximo de intentos por filling mode (default: 5)
    
    Returns:
        bool: True si la operación se cerró exitosamente, False en caso contrario
    """
    # Lista de filling modes a probar en orden de preferencia
    filling_modes = [
        ("FOK", mt5.ORDER_FILLING_FOK),
        ("IOC", mt5.ORDER_FILLING_IOC), 
        ("RETURN", mt5.ORDER_FILLING_RETURN)
    ]
    
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
        else:
            order_type = mt5.ORDER_TYPE_BUY
        
        if logger:
            logger.log(f"Intentando cerrar operación {ticket} con múltiples filling modes...")
        
        # Probar cada filling mode hasta max_attempts veces
        for mode_name, filling_mode in filling_modes:
            if logger:
                logger.log(f"Probando filling mode: {mode_name}")
            
            for attempt in range(1, max_attempts + 1):
                try:
                    # Obtener precio actual
                    tick = mt5.symbol_info_tick(position.symbol)
                    if not tick:
                        if logger:
                            logger.error(f"No se pudo obtener precio para {position.symbol}")
                        continue
                    
                    price = tick.bid if position.type == mt5.POSITION_TYPE_BUY else tick.ask
                    
                    # Crear la solicitud de cierre
                    close_request = {
                        "action": mt5.TRADE_ACTION_DEAL,
                        "symbol": position.symbol,
                        "volume": position.volume,
                        "type": order_type,
                        "position": ticket,
                        "price": price,
                        "deviation": 20,
                        "magic": position.magic,
                        "comment": f"Cerrar {ticket} - {mode_name} - Intento {attempt}",
                        "type_time": mt5.ORDER_TIME_GTC,
                        "type_filling": filling_mode,
                    }
                    
                    # Enviar la orden de cierre
                    result = mt5.order_send(close_request)
                    
                    if result is None:
                        if logger:
                            logger.error(f"Intento {attempt}/{max_attempts} ({mode_name}): order_send() falló")
                        time.sleep(0.5)  # Esperar antes del siguiente intento
                        continue
                    
                    if result.retcode == mt5.TRADE_RETCODE_DONE:
                        # ¡Éxito! Operación cerrada
                        profit_loss = position.profit
                        trade_type = "Long" if position.type == mt5.POSITION_TYPE_BUY else "Short"
                        
                        if logger:
                            timestamp = datetime.now().strftime("%H:%M:%S")
                            logger.success(f"[{timestamp}] ✅ Operación cerrada exitosamente!")
                            logger.log(f"Ticket: {ticket} | Tipo: {trade_type} | "
                                      f"Volumen: {position.volume:.2f} | P/L: {profit_loss:.2f} $ | "
                                      f"Precio cierre: {price:.5f} | Método: {mode_name} (Intento {attempt})")
                        
                        return True
                    
                    else:
                        # Error en este intento
                        if logger:
                            logger.error(f"Intento {attempt}/{max_attempts} ({mode_name}): "
                                       f"{result.comment} (código: {result.retcode})")
                        
                        # Si es el último intento con este filling mode, no esperar
                        if attempt < max_attempts:
                            time.sleep(0.5)  # Esperar antes del siguiente intento
                
                except Exception as e:
                    if logger:
                        logger.error(f"Excepción en intento {attempt}/{max_attempts} ({mode_name}): {e}")
                    if attempt < max_attempts:
                        time.sleep(0.5)
        
        # Si llegamos aquí, no se pudo cerrar con ningún método
        if logger:
            logger.error(f"❌ No se pudo cerrar la operación {ticket} después de {max_attempts * len(filling_modes)} intentos")
        
        return False
        
    except Exception as e:
        if logger:
            logger.error(f"Excepción crítica al cerrar operación {ticket}: {e}")
        return False