import MetaTrader5 as mt5
import time

# -----------------------------
# Configuraciones generales
# -----------------------------
MAX_SPREAD_PIPS = 2.0     # Spread máximo tolerado en pips
VERIFY_TIMEOUT = 10       # Segundos para verificar cierre completo
MAX_ATTEMPTS = 5          # Intentos por filling mode

# -----------------------------
# Función de traducción de errores (opcional)
# -----------------------------
try:
    from metatrader.metatrader import obtener_mensaje_error
except ImportError:
    def obtener_mensaje_error(codigo_error: int) -> str:
        return f"Error desconocido (código: {codigo_error})"

# -----------------------------
# Función interna de verificación
# -----------------------------
def _verify_position_closed(ticket, logger=None, timeout=VERIFY_TIMEOUT):
    """Verifica que la posición se haya cerrado completamente después de enviar la orden."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        remaining = mt5.positions_get(ticket=ticket)
        if not remaining:
            if logger:
                logger.success(f"✅ La posición {ticket} está cerrada.")
            return True
        
        if logger:
            logger.log(f"Aguardando cierre completo de {ticket}. Volumen restante: {remaining[0].volume}", "warning")
        
        time.sleep(0.5)

    final = mt5.positions_get(ticket=ticket)
    if final and logger:
        logger.error(f"❌ Falló el cierre de {ticket}. Volumen restante: {final[0].volume}")
    return not final

# -----------------------------
# Cierre robusto de una operación
# -----------------------------
def close_operation_robust(ticket, logger=None, max_attempts=MAX_ATTEMPTS, max_spread_pips=MAX_SPREAD_PIPS):
    """Cierra una operación de forma robusta minimizando riesgo de slippage y pérdidas."""
    filling_modes = [
        ("FOK", mt5.ORDER_FILLING_FOK),
        ("IOC", mt5.ORDER_FILLING_IOC),
        ("RETURN", mt5.ORDER_FILLING_RETURN),
    ]

    try:
        # Obtener posición
        position = mt5.positions_get(ticket=ticket)
        if not position:
            if logger:
                logger.error(f"No se encontró la posición {ticket}")
            return False
        position = position[0]

        # Info del símbolo
        symbol_info = mt5.symbol_info(position.symbol)
        if not symbol_info:
            if logger:
                logger.error(f"No se pudo obtener info del símbolo {position.symbol}")
            return False

        # Volumen seguro
        volume_step = symbol_info.volume_step
        volume = max(volume_step, round(position.volume / volume_step) * volume_step)

        if logger:
            logger.log(f"🔍 Intentando cerrar {volume:.2f} lotes de {position.symbol} (ticket {ticket})")

        # Tipo de orden opuesta
        order_type = mt5.ORDER_TYPE_SELL if position.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY

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

                # Precio de cierre
                price = tick.bid if position.type == mt5.POSITION_TYPE_BUY else tick.ask

                # Spread en pips
                spread_pips = (symbol_info.ask - symbol_info.bid) / symbol_info.point
                if spread_pips > max_spread_pips and logger:
                    logger.warning(f"⚠️ Spread alto: {spread_pips:.1f} pips. Riesgo de slippage.")

                # Deviation dinámico
                deviation = max(int(spread_pips * 1.5), 5)

                # Comentario corto
                comment_text = f"C{ticket}_{mode_name}_{attempt}"[:20]

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
                        logger.error(f"Intento {attempt}/{max_attempts} ({mode_name}): order_send() falló - {err}")
                    time.sleep(0.5)
                    continue

                if result.retcode == mt5.TRADE_RETCODE_DONE:
                    if logger:
                        logger.success(f"✅ Orden de cierre enviada para {ticket} con {mode_name} "
                                       f"(Vol {volume:.2f}, Precio {price:.5f})")
                    return _verify_position_closed(ticket, logger)

                else:
                    error_traducido = obtener_mensaje_error(result.retcode)
                    if logger:
                        logger.error(f"Intento {attempt}/{max_attempts} ({mode_name}): "
                                     f"{result.comment} (código {result.retcode} - {error_traducido})")

                    # Cierre parcial seguro
                    if "invalid volume" in result.comment.lower() or result.retcode in (
                        mt5.TRADE_RETCODE_INVALID_VOLUME,
                        mt5.TRADE_RETCODE_INVALID_PRICE,
                    ):
                        partial_volume = round((volume - volume_step) / volume_step) * volume_step
                        if partial_volume >= volume_step:
                            if logger:
                                logger.log(f"🔄 Intentando cierre parcial: {partial_volume:.2f} lotes")
                            close_request["volume"] = partial_volume
                            partial_result = mt5.order_send(close_request)
                            if partial_result and partial_result.retcode == mt5.TRADE_RETCODE_DONE:
                                if logger:
                                    logger.success(f"✅ Cierre parcial enviado: {partial_volume:.2f} lotes")
                                return _verify_position_closed(ticket, logger)

                    time.sleep(0.5)

        if logger:
            logger.error(f"❌ No se pudo cerrar la operación {ticket} tras {max_attempts * len(filling_modes)} intentos")
        return False

    except Exception as e:
        if logger:
            logger.error(f"Excepción crítica al cerrar operación {ticket}: {e}")
        return False

# -----------------------------
# Cierre de una sola operación
# -----------------------------
def close_single_operation(ticket, logger=None):
    return close_operation_robust(ticket, logger)

# -----------------------------
# Cierre de todas las operaciones de un símbolo
# -----------------------------
def close_all_operations(symbol, logger=None):
    try:
        positions = mt5.positions_get(symbol=symbol)
        if not positions:
            if logger:
                logger.log(f"No hay operaciones abiertas para {symbol}")
            return {"total": 0, "cerradas": 0, "fallidas": 0, "p_l_total": 0.0}

        total = len(positions)
        cerradas = 0
        p_l_total = 0.0

        if logger:
            logger.log(f"Cerrando {total} operaciones para {symbol} con método robusto...")

        for pos in positions:
            success = close_operation_robust(pos.ticket, logger)
            if success:
                cerradas += 1
                p_l_total += pos.profit

        fallidas = total - cerradas

        if logger:
            logger.log(f"✅ Resumen de cierre para {symbol}: Total: {total}, Cerradas: {cerradas}, "
                       f"Fallidas: {fallidas}, P/L total: {p_l_total:.2f} $")

        return {
            "total": total,
            "cerradas": cerradas,
            "fallidas": fallidas,
            "p_l_total": p_l_total
        }

    except Exception as e:
        if logger:
            logger.error(f"Error al cerrar todas las operaciones para {symbol}: {e}")
        return {"total": 0, "cerradas": 0, "fallidas": 0, "p_l_total": 0.0}
