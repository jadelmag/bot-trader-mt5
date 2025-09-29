import MetaTrader5 as mt5
from datetime import datetime
import time

# Importar la función de traducción de errores
try:
    from metatrader.metatrader import obtener_mensaje_error
except ImportError:
    def obtener_mensaje_error(codigo_error: int) -> str:
        return f"Error desconocido (código: {codigo_error})"

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
    Incluye manejo de filling modes, retries, precios actualizados y
    cierre parcial en caso necesario.
    """

    filling_modes = [
        ("FOK", mt5.ORDER_FILLING_FOK),
        ("IOC", mt5.ORDER_FILLING_IOC),
        ("RETURN", mt5.ORDER_FILLING_RETURN),
    ]

    try:
        # Obtener la posición
        position = mt5.positions_get(ticket=ticket)
        if not position:
            if logger:
                logger.error(f"No se encontró la posición con ticket {ticket}")
            return False
        position = position[0]

        # Info del símbolo
        symbol_info = mt5.symbol_info(position.symbol)
        if not symbol_info:
            if logger:
                logger.error(f"No se pudo obtener info del símbolo {position.symbol}")
            return False

        # Redondear volumen al step permitido
        volume_step = symbol_info.volume_step
        volume = round(position.volume / volume_step) * volume_step

        if logger:
            logger.log(f"🔍 Intentando cerrar {volume:.2f} lotes de {position.symbol} (ticket {ticket})")

        # Determinar tipo de orden opuesta
        order_type = mt5.ORDER_TYPE_SELL if position.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY

        # Probar cada filling mode
        for mode_name, filling_mode in filling_modes:
            if logger:
                logger.log(f"Probando filling mode: {mode_name}")

            for attempt in range(1, max_attempts + 1):
                tick = mt5.symbol_info_tick(position.symbol)
                if not tick:
                    if logger:
                        logger.error(f"No se pudo obtener precio para {position.symbol}")
                    time.sleep(0.5)
                    continue

                # Precios de cierre correctos según tipo
                price = tick.bid if position.type == mt5.POSITION_TYPE_BUY else tick.ask

                # Deviation dinámico en función del spread
                deviation = max(20, int(symbol_info.spread * 2))

                # Generar un comentario corto y válido
                comment_text = f"C{ticket}_{mode_name}_{attempt}"
                if len(comment_text) > 20:
                    comment_text = comment_text[:20]

                close_request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": position.symbol,
                    "volume": volume,
                    "type": order_type,
                    "position": ticket,
                    "price": price,
                    "deviation": deviation,
                    "magic": position.magic,
                    "comment": comment_text,
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": filling_mode,
                }

                result = mt5.order_send(close_request)

                if result is None:
                    err = mt5.last_error()
                    if logger:
                        logger.error(f"Intento {attempt}/{max_attempts} ({mode_name}): "
                                     f"order_send() falló - {err}")
                    time.sleep(0.5)
                    continue

                if result.retcode == mt5.TRADE_RETCODE_DONE:
                    if logger:
                        logger.success(f"✅ Operación {ticket} cerrada con {mode_name} "
                                       f"(Intento {attempt}, Vol {volume:.2f}, Precio {price:.5f})")
                    return True
                else:
                    error_traducido = obtener_mensaje_error(result.retcode)
                    if logger:
                        logger.error(f"Intento {attempt}/{max_attempts} ({mode_name}): "
                                     f"{result.comment} (código: {result.retcode} - {error_traducido})")

                    # Si falla con el volumen completo, intentar parcial
                    if "invalid volume" in result.comment.lower() or result.retcode in (
                        mt5.TRADE_RETCODE_INVALID_VOLUME,
                        mt5.TRADE_RETCODE_INVALID_PRICE,
                    ):
                        partial_volume = max(volume_step, volume - volume_step)
                        if partial_volume < volume:
                            if logger:
                                logger.log(f"🔄 Intentando cerrar parcialmente {partial_volume:.2f} lotes...")
                            close_request["volume"] = partial_volume
                            partial_result = mt5.order_send(close_request)
                            if partial_result and partial_result.retcode == mt5.TRADE_RETCODE_DONE:
                                if logger:
                                    logger.success(f"✅ Cierre parcial exitoso: {partial_volume:.2f} lotes")
                                return True

                    time.sleep(0.5)

        if logger:
            logger.error(f"❌ No se pudo cerrar la operación {ticket} tras {max_attempts * len(filling_modes)} intentos")

        return False

    except Exception as e:
        if logger:
            logger.error(f"Excepción crítica al cerrar operación {ticket}: {e}")
        return False
