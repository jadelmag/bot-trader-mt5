import os
import json
import pandas as pd

# --- Path Setup ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, '..'))
CONFIG_PATH = os.path.join(PROJECT_ROOT, "strategies", "config.json")


class ConfigLoader:
    """Maneja la carga de configuraciones del sistema."""
    
    def __init__(self, logger=None):
        self.logger = logger
    
    def _log(self, message, level='info'):
        """Helper para registrar mensajes."""
        if self.logger:
            log_methods = {
                'info': self.logger.log,
                'success': self.logger.success,
                'error': self.logger.error,
                'warn': self.logger.warn
            }
            log_methods.get(level, self.logger.log)(message)
        else:
            print(message)
    
    def load_general_config(self):
        """Carga la configuración general desde config.json."""
        if not os.path.exists(CONFIG_PATH):
            return {}
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, TypeError):
            self._log("[CONFIG-ERROR] El archivo de configuración general 'config.json' está corrupto.", 'error')
            return {}
    
    def load_candle_pattern_config(self, pattern_name):
        """Carga la configuración JSON para un patrón de vela específico."""
        config_filename = f"{pattern_name.replace('is_', '')}.json"
        config_path = os.path.join(PROJECT_ROOT, "strategies", config_filename)
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                self._log(f"[CONFIG-WARN] Error al cargar config para '{pattern_name}': {e}. Usando valores por defecto.", 'warn')
        return {}
    
    @staticmethod
    def get_timeframe_delta(timeframe_str):
        """Convierte un string de timeframe a pandas Timedelta."""
        mapping = {
            "M1": pd.Timedelta(minutes=1),
            "M5": pd.Timedelta(minutes=5),
            "M15": pd.Timedelta(minutes=15),
            "M30": pd.Timedelta(minutes=30),
            "H1": pd.Timedelta(hours=1),
            "H4": pd.Timedelta(hours=4),
            "D1": pd.Timedelta(days=1),
        }
        return mapping.get(timeframe_str.upper())