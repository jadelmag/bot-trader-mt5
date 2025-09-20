import MetaTrader5 as mt5
import os
from dotenv import load_dotenv

# Carga las variables de entorno desde el archivo .env
load_dotenv()

class LoginMT5:
    def __init__(self, account=None, password=None, server=None):
        """
        Inicializa la conexión a MetaTrader 5.
        Las credenciales se pueden pasar directamente o se leerán desde variables de entorno.
        """
        self.account = int(account) if account else int(os.getenv("MT5_ACCOUNT", "0"))
        self.password = password if password else os.getenv("MT5_PASSWORD", "")
        self.server = server if server else os.getenv("MT5_SERVER", "")
        mt5.initialize()

    def login(self):
        if not self.account or not self.password or not self.server:
            print("Error: Faltan credenciales. Proporciónelas al conectar o en el archivo .env.")
            return False
        connected = mt5.login(self.account, self.password, self.server)
        return connected
