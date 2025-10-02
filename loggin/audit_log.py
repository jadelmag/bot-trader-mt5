import os
import json
from datetime import datetime

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "strategies", "config.json")
AUDIT_DIR = os.path.join(os.path.dirname(__file__), "..", "audit")

class AuditLogger:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(AuditLogger, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        # Evitar reinicialización
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self.is_enabled = False
        self.log_file_path = None
        self._load_config()
        
        if self.is_enabled:
            self._setup_log_file()
        
        self._initialized = True

    def _load_config(self):
        """Carga la configuración para determinar si el logger debe estar activo."""
        try:
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    config = json.load(f)
                self.is_enabled = config.get("audit_log_enabled", False)
        except (json.JSONDecodeError, IOError):
            self.is_enabled = False # Si hay error, se deshabilita por seguridad

    def _setup_log_file(self):
        """Prepara el archivo de log para la sesión actual."""
        if not self.is_enabled:
            return
        try:
            os.makedirs(AUDIT_DIR, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.log_file_path = os.path.join(AUDIT_DIR, f"audit_log_{timestamp}.jsonl")
        except OSError:
            self.is_enabled = False # No se pudo crear el directorio o archivo

    def log_message(self, message: str, level: str = "INFO"):
        """Registra un mensaje general en el log."""
        if not self.is_enabled or not self.log_file_path:
            return

        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "event": "log_message",
                "data": {
                    "level": level,
                    "message": message
                }
            }
            with open(self.log_file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[ERROR] No se pudo escribir en el log: {e}")

    def log_event(self, event_type: str, data: dict):
        """Registra un evento en el archivo de log si está habilitado."""
        if not self.is_enabled or not self.log_file_path:
            return

        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "event": event_type,
                "data": data
            }
            with open(self.log_file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception:
            # Evitar que un error de logging detenga la aplicación
            pass

    def log_trade_open(self, symbol: str, trade_type: str, volume: float, price: float, sl: float, tp: float, comment: str = ""):
        """Registra la apertura de una operación."""
        data = {
            "symbol": symbol,
            "type": trade_type,
            "volume": volume,
            "open_price": price,
            "stop_loss": sl,
            "take_profit": tp,
            "comment": comment
        }
        self.log_event("trade_open", data)

    def log_trade_close(self, ticket: int, symbol: str, close_price: float, profit: float):
        """Registra el cierre de una operación."""
        data = {
            "ticket": ticket,
            "symbol": symbol,
            "close_price": close_price,
            "profit": profit
        }
        self.log_event("trade_close", data)

    def log_system_event(self, message: str, level: str = "INFO"):
        """Registra un evento general del sistema."""
        data = {
            "level": level,
            "message": message
        }
        self.log_event("system_event", data)


# Singleton instance for easy access throughout the application
audit_logger = AuditLogger()
