import MetaTrader5 as mt5
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# ==============================
# Credenciales de conexión
# ==============================
MT5_ACCOUNT = int(os.getenv("MT5_ACCOUNT"))
MT5_PASSWORD = os.getenv("MT5_PASSWORD")
MT5_SERVER = os.getenv("MT5_SERVER")

# ==============================
# Conexión a MetaTrader 5
# ==============================
path_to_terminal = "C:\\Program Files\\MetaTrader 5\\terminal64.exe"
if not mt5.initialize(path=path_to_terminal):
    print("❌ No se pudo inicializar MetaTrader 5")
    print("Error de inicialización:", mt5.last_error())
    mt5.shutdown()
    quit()

authorized = mt5.login(MT5_ACCOUNT, password=MT5_PASSWORD, server=MT5_SERVER)
if not authorized:
    print("❌ No se pudo conectar con la cuenta")
    print("Error:", mt5.last_error())
    mt5.shutdown()
    quit()

print(f"✅ Conectado a la cuenta {MT5_ACCOUNT} en {MT5_SERVER}")

# ==============================
# Consultar parámetros del símbolo
# ==============================
symbol = "EURUSD"  # cambia el símbolo si quieres otro
info = mt5.symbol_info(symbol)

if info is None:
    print(f"❌ No se pudo obtener información del símbolo {symbol}")
else:
    print(f"📊 Parámetros de {symbol}:")
    print(f"   - Volumen mínimo permitido: {info.volume_min}")
    print(f"   - Volumen máximo permitido: {info.volume_max}")
    print(f"   - Paso de volumen: {info.volume_step}")

# ==============================
# Cerrar conexión
# ==============================
mt5.shutdown()
