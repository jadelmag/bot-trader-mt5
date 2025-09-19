import MetaTrader5 as mt5
import os
from dotenv import load_dotenv

# Carga las variables de entorno desde el archivo .env
load_dotenv()

class LoginMT5:
    def __init__(self):
        # Lee las credenciales desde las variables de entorno
        self.account = int(os.getenv("MT5_ACCOUNT", 0))
        self.password = os.getenv("MT5_PASSWORD", "")
        self.server = os.getenv("MT5_SERVER", "")
        mt5.initialize()

    def login(self):
        if not self.account or not self.password or not self.server:
            print("Error: Faltan credenciales en el archivo .env o están vacías.")
            return False
        connected = mt5.login(self.account, self.password, self.server)
        return connected
