import os
import json

PREFS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "user_prefs.json")

class PreferencesManager:
    def __init__(self, app):
        self.app = app

    def load(self):
        """Carga las preferencias de símbolo y timeframe desde el archivo JSON."""
        try:
            if os.path.exists(PREFS_PATH):
                with open(PREFS_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                sym = data.get("symbol")
                tf = data.get("timeframe")
                if isinstance(sym, str) and sym:
                    self.app.symbol_var.set(sym)
                if isinstance(tf, str) and tf:
                    self.app.timeframe_var.set(tf)
        except Exception:
            # Ignorar JSON malformado o errores de lectura
            pass

    def save(self, symbol: str = None, timeframe: str = None):
        """Guarda las preferencias de símbolo y timeframe en el archivo JSON."""
        try:
            data = {}
            if os.path.exists(PREFS_PATH):
                try:
                    with open(PREFS_PATH, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    data = {}
            
            if symbol is not None:
                data["symbol"] = symbol
            if timeframe is not None:
                data["timeframe"] = timeframe
            
            with open(PREFS_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            # No bloquear la UI por errores de guardado
            pass
