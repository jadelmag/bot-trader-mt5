# cerrar_operaciones_emergencia.py
import MetaTrader5 as mt5
import time
import sys

def obtener_mensaje_error(codigo_error):
    """
    Traduce códigos de error de MT5 a mensajes comprensibles
    """
    errores = {
        10004: "Requote",
        10006: "No hay precios",
        10007: "Broker ocupado",
        10008: "Operación en tiempo de expiración",
        10010: "Orden inválida",
        10013: "Volumen inválido",
        10014: "Precio inválido",
        10015: "Símbolo inválido",
        10016: "Demasiadas solicitudes",
        10017: "Cambio no permitido",
        10018: "Mercado cerrado",
        10019: "Fondos insuficientes",
        10020: "Operación prohibida",
        10021: "Margen insuficiente",
        10027: "Requote - precio cambiado",
    }
    return errores.get(codigo_error, f"Error desconocido: {codigo_error}")

def mostrar_operaciones_abiertas():
    """
    Muestra todas las operaciones abiertas
    """
    print("\n=== OPERACIONES ABIERTAS ACTUALES ===")
    positions = mt5.positions_get()
    if not positions:
        print("No hay operaciones abiertas")
        return []
    
    for i, pos in enumerate(positions):
        tipo = "COMPRA" if pos.type == 0 else "VENTA"
        print(f"{i+1}. Ticket: {pos.ticket} | {pos.symbol} | {tipo} | Volumen: {pos.volume} | Comentario: '{pos.comment}'")
    
    return positions

def cerrar_operacion_individual(position, metodo="normal"):
    """
    Cierra una operación individual
    """
    try:
        tick = mt5.symbol_info_tick(position.symbol)
        if not tick:
            print(f"❌ No se pudo obtener precio para {position.symbol}")
            return False
        
        if position.type == 0:  # ORDER_TYPE_BUY
            order_type = 1  # ORDER_TYPE_SELL
            price = tick.bid
            tipo_str = "COMPRA → VENTA"
        else:  # ORDER_TYPE_SELL
            order_type = 0  # ORDER_TYPE_BUY
            price = tick.ask
            tipo_str = "VENTA → COMPRA"
        
        if metodo == "agresivo":
            deviation = 100
            filling = mt5.ORDER_FILLING_FOK
            comentario = "CIERRE AGRESIVO"
        else:
            deviation = 20
            filling = mt5.ORDER_FILLING_IOC
            comentario = "CIERRE NORMAL"
        
        close_request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": position.ticket,
            "symbol": position.symbol,
            "volume": position.volume,
            "type": order_type,
            "price": price,
            "deviation": deviation,
            "magic": position.magic,
            "comment": comentario,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": filling,
        }
        
        print(f"💰 Cerrando {position.ticket} ({tipo_str}) a {price:.5f}")
        
        result = mt5.order_send(close_request)
        
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"✅ OPERACIÓN {position.ticket} CERRADA EXITOSAMENTE")
            return True
        else:
            print(f"❌ Error {result.retcode}: {obtener_mensaje_error(result.retcode)}")
            return False
            
    except Exception as e:
        print(f"💥 Excepción al cerrar {position.ticket}: {e}")
        return False

def cerrar_por_comentario(comment_filter="custom Pico y Pala", metodo="normal"):
    """
    Cierra operaciones filtradas por comentario
    """
    positions = mt5.positions_get()
    if not positions:
        print("No hay operaciones abiertas")
        return True
    
    bot_positions = [p for p in positions if comment_filter in p.comment]
    
    if not bot_positions:
        print(f"No hay operaciones con comentario: '{comment_filter}'")
        return True
    
    print(f"\n🔍 Encontradas {len(bot_positions)} operaciones con comentario '{comment_filter}'")
    
    exitos = 0
    for i, position in enumerate(bot_positions, 1):
        print(f"\n--- Cerrando operación {i}/{len(bot_positions)} ---")
        if cerrar_operacion_individual(position, metodo):
            exitos += 1
        time.sleep(1)  # Pausa entre cierres
    
    print(f"\n📊 Resultado: {exitos}/{len(bot_positions)} operaciones cerradas")
    return exitos == len(bot_positions)

def cerrar_todas_las_operaciones(metodo="normal"):
    """
    Cierra TODAS las operaciones abiertas
    """
    positions = mt5.positions_get()
    if not positions:
        print("No hay operaciones abiertas")
        return True
    
    print(f"\n🚨 CERRANDO TODAS LAS {len(positions)} OPERACIONES ABIERTAS")
    
    exitos = 0
    for i, position in enumerate(positions, 1):
        print(f"\n--- Cerrando operación {i}/{len(positions)} ---")
        if cerrar_operacion_individual(position, metodo):
            exitos += 1
        time.sleep(1)
    
    print(f"\n📊 Resultado: {exitos}/{len(positions)} operaciones cerradas")
    return exitos == len(positions)

def menu_principal():
    """
    Menú interactivo para seleccionar el método de cierre
    """
    print("=" * 60)
    print("🔧 CERRADOR DE EMERGENCIA - META TRADER 5")
    print("=" * 60)
    
    # Mostrar operaciones actuales
    positions = mostrar_operaciones_abiertas()
    
    if not positions:
        return
    
    print("\n🎯 OPCIONES DE CIERRE:")
    print("1. Cerrar operaciones con comentario 'custom Pico y Pala' (Método Normal)")
    print("2. Cerrar operaciones con comentario 'custom Pico y Pala' (Método Agresivo)")
    print("3. Cerrar TODAS las operaciones (Método Normal)")
    print("4. Cerrar TODAS las operaciones (Método Agresivo)")
    print("5. Salir")
    
    try:
        opcion = input("\nSelecciona una opción (1-5): ").strip()
        
        if opcion == "1":
            cerrar_por_comentario("custom Pico y Pala", "normal")
        elif opcion == "2":
            cerrar_por_comentario("custom Pico y Pala", "agresivo")
        elif opcion == "3":
            cerrar_todas_las_operaciones("normal")
        elif opcion == "4":
            cerrar_todas_las_operaciones("agresivo")
        elif opcion == "5":
            print("Saliendo...")
        else:
            print("Opción inválida")
    
    except KeyboardInterrupt:
        print("\nOperación cancelada por el usuario")
    except Exception as e:
        print(f"Error: {e}")

def main():
    """
    Función principal
    """
    print("Inicializando MetaTrader 5...")
    
    # Inicializar MT5
    if not mt5.initialize():
        print("❌ No se pudo inicializar MetaTrader 5")
        print("⚠️  Asegúrate de que:")
        print("   - MetaTrader 5 esté instalado")
        print("   - La terminal esté abierta")
        print("   - Tengas cuenta demo/real conectada")
        input("Presiona Enter para salir...")
        return
    
    print("✅ MetaTrader 5 inicializado correctamente")
    
    try:
        # Mostrar información de la cuenta
        account_info = mt5.account_info()
        if account_info:
            print(f"💼 Cuenta: {account_info.login} | Balance: {account_info.balance:.2f}")
        
        # Ejecutar menú
        menu_principal()
        
    except Exception as e:
        print(f"💥 Error durante la ejecución: {e}")
    finally:
        # Cerrar conexión
        mt5.shutdown()
        print("\n🔌 Conexión con MT5 cerrada")

if __name__ == "__main__":
    main()
    
    # Pausa antes de salir
    input("\nPresiona Enter para salir...")