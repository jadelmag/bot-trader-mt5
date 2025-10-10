import MetaTrader5 as mt5
import time
from datetime import datetime, timedelta

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

def _get_deal_profit(ticket, logger=None):
    """Obtiene el profit de un deal cerrado buscando en el historial reciente."""
    try:
        # Buscar en el historial de las últimas 24 horas
        from_date = datetime.now() - timedelta(hours=24)
        to_date = datetime.now()
        
        deals = mt5.history_deals_get(from_date, to_date)
        
        if deals:
            # Filtrar por el ticket de la posición/orden
            for deal in reversed(deals):  # Buscar desde el más reciente
                if deal.position_id == ticket and deal.entry == 1:  # 1 = deal de salida
                    if logger:
                        logger.log(f"Deal de cierre encontrado para ticket {ticket} con profit {deal.profit:.2f}", "info")
                    return deal.profit
        
        # Si no encontramos el deal en el historial, intentar buscar en history_deals_get por posición
        position_deals = mt5.history_deals_get(position=ticket)
        if position_deals:
            # El último deal debería ser el de cierre
            for deal in reversed(position_deals):
                if deal.entry == 1:  # 1 = deal de salida
                    if logger:
                        logger.log(f"Deal de cierre encontrado por position para {ticket} con profit {deal.profit:.2f}", "info")
                    return deal.profit

        # Si llegamos aquí, no pudimos encontrar el profit en los deals
        if logger:
            logger.warn(f"No se encontró el deal de cierre para el ticket {ticket} en el historial reciente.")
        return 0.0  # Retornar 0 si no se encuentra

    except Exception as e:
        if logger:
            logger.error(f"Excepción al buscar profit del deal para {ticket}: {e}")
        return 0.0

# -----------------------------
# Cierre robusto de una operación
# -----------------------------
def close_operation_robust(ticket, logger=None, max_attempts=MAX_ATTEMPTS, max_spread_pips=MAX_SPREAD_PIPS):
    """Cierra una operación de forma robusta y devuelve el resultado."""
    filling_modes = [
        ("FOK", mt5.ORDER_FILLING_FOK),
        ("IOC", mt5.ORDER_FILLING_IOC),
        ("RETURN", mt5.ORDER_FILLING_RETURN),
    ]

    try:
        position = mt5.positions_get(ticket=ticket)
        if not position:
            if logger:
                logger.error(f"No se encontró la posición {ticket}")
            return {"success": False, "profit": 0.0, "ticket": ticket}
        position = position[0]
        
        # Guardar el profit flotante para usarlo como fallback
        floating_profit = position.profit
        
        if logger:
            logger.log(f"P/L flotante antes de cerrar: {floating_profit:.2f} $")

        symbol_info = mt5.symbol_info(position.symbol)
        if not symbol_info:
            if logger:
                logger.error(f"No se pudo obtener info del símbolo {position.symbol}")
            return {"success": False, "profit": 0.0, "ticket": ticket}

        volume_step = symbol_info.volume_step
        volume = max(volume_step, round(position.volume / volume_step) * volume_step)

        if logger:
            logger.log(f"🔍 Intentando cerrar {volume:.2f} lotes de {position.symbol} (ticket {ticket})")

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

                price = tick.bid if position.type == mt5.POSITION_TYPE_BUY else tick.ask
                spread_pips = (symbol_info.ask - symbol_info.bid) / symbol_info.point
                if spread_pips > max_spread_pips and logger:
                    logger.warn(f"⚠️ Spread alto: {spread_pips:.1f} pips.")

                deviation = max(int(spread_pips * 1.5), 5)
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
                        logger.success(f"✅ Orden de cierre enviada para {ticket} con {mode_name}")
                    
                    if _verify_position_closed(ticket, logger):
                        # Intentar obtener el profit del deal, si falla usar el flotante
                        profit = _get_deal_profit(ticket, logger)
                        if profit == 0.0 and floating_profit != 0.0:
                            if logger:
                                logger.log(f"Usando P/L flotante guardado ({floating_profit:.2f}) en lugar de 0.0")
                            profit = floating_profit
                        return {"success": True, "profit": profit, "ticket": ticket}
                    else:
                        return {"success": False, "profit": 0.0, "ticket": ticket}

                else:
                    error_traducido = obtener_mensaje_error(result.retcode)
                    if logger:
                        logger.error(f"Intento {attempt}/{max_attempts} ({mode_name}): {result.comment} (código {result.retcode} - {error_traducido})")
                    time.sleep(0.5)

        if logger:
            logger.error(f"❌ No se pudo cerrar la operación {ticket} tras {max_attempts * len(filling_modes)} intentos")
        return {"success": False, "profit": 0.0, "ticket": ticket}

    except Exception as e:
        if logger:
            logger.error(f"Excepción crítica al cerrar operación {ticket}: {e}")
        return {"success": False, "profit": 0.0, "ticket": ticket}

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
            result = close_operation_robust(pos.ticket, logger)
            if result and result.get("success"):
                cerradas += 1
                p_l_total += result.get("profit", pos.profit) # Usa profit del deal si está, si no, el flotante

        fallidas = total - cerradas

        if logger:
            logger.log(f"✅ Resumen de cierre para {symbol}: Total: {total}, Cerradas: {cerradas}, Fallidas: {fallidas}, P/L total: {p_l_total:.2f} $")

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