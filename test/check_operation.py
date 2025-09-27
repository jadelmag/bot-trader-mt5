import MetaTrader5 as mt5
import time
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Credenciales
ACCOUNT = int(os.getenv("MT5_ACCOUNT"))
PASSWORD = os.getenv("MT5_PASSWORD")
SERVER = os.getenv("MT5_SERVER")

# Inicializar MT5
if not mt5.initialize(login=ACCOUNT, password=PASSWORD, server=SERVER):
    print("❌ No se pudo inicializar MT5:", mt5.last_error())
    quit()

print("✅ Conectado a MT5")

# Definir símbolo
symbol = "EURUSD"

# Asegurar que el símbolo esté disponible
if not mt5.symbol_select(symbol, True):
    print(f"❌ No se pudo seleccionar el símbolo {symbol}")
    mt5.shutdown()
    quit()

# Volumen mínimo permitido
volume = 0.01  

# Crear orden de compra (long)
request = {
    "action": mt5.TRADE_ACTION_DEAL,
    "symbol": symbol,
    "volume": volume,
    "type": mt5.ORDER_TYPE_BUY,
    "price": mt5.symbol_info_tick(symbol).ask,
    "deviation": 20,
    "magic": 123456,
    "comment": "Test Buy",
    "type_filling": mt5.ORDER_FILLING_FOK,
}

# Enviar orden
result = mt5.order_send(request)
if result.retcode != mt5.TRADE_RETCODE_DONE:
    print("❌ Error al enviar la orden:", result)
    mt5.shutdown()
    quit()

print(f"✅ Orden BUY abierta: ticket={result.order}")

# Esperar unos segundos
time.sleep(3)

# Cerrar posición abierta
positions = mt5.positions_get(symbol=symbol)
if positions:
    position = positions[0]
    close_request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": position.symbol,
        "volume": position.volume,
        "type": mt5.ORDER_TYPE_SELL,
        "position": position.ticket,
        "price": mt5.symbol_info_tick(symbol).bid,
        "deviation": 20,
        "magic": 123456,
        "comment": "Test Close",
        "type_filling": mt5.ORDER_FILLING_FOK,
    }
    close_result = mt5.order_send(close_request)
    if close_result.retcode == mt5.TRADE_RETCODE_DONE:
        print(f"✅ Posición cerrada: ticket={close_result.order}")
    else:
        print("❌ Error al cerrar la posición:", close_result)
else:
    print("⚠️ No se encontró ninguna posición abierta para cerrar.")

# Apagar MT5
mt5.shutdown()
