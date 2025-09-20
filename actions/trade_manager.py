import os
import json

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "strategies", "config.json")

class TradeManager:
    """Gestiona las reglas de negocio para la apertura y cierre de operaciones."""

    def __init__(self):
        self.money_limit = 0.0
        self.is_enabled = False
        self._load_config()

    def _load_config(self):
        """Carga la configuración del límite de dinero desde el archivo JSON."""
        try:
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    config = json.load(f)
                
                limit = config.get("money_limit", 0.0)
                if limit > 0:
                    self.money_limit = limit
                    self.is_enabled = True
                else:
                    self.is_enabled = False
        except (json.JSONDecodeError, IOError):
            self.is_enabled = False # Deshabilitado si hay error

    def can_open_trade(self) -> (bool, str):
        """Verifica si se puede abrir una nueva operación según el límite de dinero.

        Returns:
            tuple[bool, str]: (True, "") si se puede operar, (False, "Mensaje de error") si no.
        """
        if not self.is_enabled:
            return True, "El límite de dinero no está activado."

        if not mt5 or not mt5.terminal_info():
            return False, "No hay conexión con MetaTrader 5."

        try:
            account_info = mt5.account_info()
            if not account_info:
                return False, "No se pudo obtener la información de la cuenta."

            current_balance = account_info.balance

            if current_balance <= self.money_limit:
                message = f"Límite de dinero alcanzado. Balance actual ({current_balance:.2f} $) <= Límite ({self.money_limit:.2f} $)." 
                return False, message
            
            return True, f"El balance actual ({current_balance:.2f} $) está por encima del límite ({self.money_limit:.2f} $)."

        except Exception as e:
            return False, f"Error al verificar el límite de dinero: {e}"

    def reload_config(self):
        """Recarga la configuración para aplicar cambios sin reiniciar."""
        self._load_config()

# Instancia Singleton para un acceso fácil
trade_manager = TradeManager()
