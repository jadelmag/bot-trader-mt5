


def obtener_mensaje_error(codigo_error: int) -> str:
    """
    Traduce códigos de error de MT5 (trade return codes y errores de la API) a mensajes humanos.
    """
    errores = {
        # Códigos de retorno del servidor de trading (MQL5) :contentReference[oaicite:1]{index=1}
        10004: "Requote (precio cambiado durante ejecución)",
        10006: "Rechazo de la solicitud (request rejected)",
        10007: "Cancelado por el usuario o EA",
        10008: "Orden colocada (placed)",
        10009: "Operación completada (done)",
        10010: "Completado parcialmente (done partial)",
        10011: "Error procesando la petición (trade server error)",
        10012: "Timeout / solicitud cancelada por tiempo",
        10013: "Solicitud inválida (invalid request)",
        10014: "Volumen inválido (invalid volume)",
        10015: "Precio inválido (invalid price)",
        10016: "Stops inválidos (invalid stops)",
        10017: "Trading deshabilitado (trade disabled)",
        10018: "Mercado cerrado (market closed)",
        10019: "Fondos insuficientes (not enough money)",
        10020: "Precio cambiado / off quotes (price off / price changed)",
        10021: "No hay cotizaciones (price off, no quotes)",
        10022: "Expiración inválida (invalid expiration)",
        10023: "Orden cambiada (order state changed)",
        10024: "Demasiadas solicitudes (too many requests)",
        10025: "Sin cambios en la petición (no changes in request)",
        10026: "Autotrading deshabilitado en servidor (server disables auto-trading)",
        10027: "Auto-trading deshabilitado en cliente (client disables auto-trading)",
        10028: "Bloqueado (request locked for processing)",
        10029: "Congelado (orden o posición congelada)",
        10030: "Modo de llenado no válido / no soportado (invalid filling type)",
        10031: "Sin conexión con servidor de trading (connection error)",
        10032: "Solo permitido para cuentas reales (live account only)",
        # (Podrías extender hasta 10033 etc según el broker / plataforma)
        
        # Errores de la API de MetaTrader5 en Python (last_error) :contentReference[oaicite:2]{index=2}
        1: "Operación exitosa (generic success)",  # RES_S_OK
        -1: "Error genérico (generic fail)",        # RES_E_FAIL
        -2: "Parámetros inválidos (invalid arguments / parameters)",  # RES_E_INVALID_PARAMS
        -3: "Memoria insuficiente (no memory)",    # RES_E_NO_MEMORY
        -4: "No encontrado (not found)",           # RES_E_NOT_FOUND
        -5: "Versión inválida / incompatible (invalid version)",  # RES_E_INVALID_VERSION
        -6: "Autorización fallida (authorization failed)",         # RES_E_AUTH_FAILED
        -7: "Método no soportado (unsupported method)",            # RES_E_UNSUPPORTED
        -8: "Auto-trading deshabilitado (auto-trading disabled)",  # RES_E_AUTO_TRADING_DISABLED
        # Podrías agregar otros códigos negativos que veas en tu entorno
    }
    return errores.get(codigo_error, f"Error desconocido (código: {codigo_error})")
