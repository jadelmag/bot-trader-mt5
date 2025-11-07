import time
import math
from datetime import datetime, timedelta
import pandas as pd
import pandas_ta as ta
import numpy as np
from datetime import datetime
import threading
from typing import Dict, List, Optional
import json
import os

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None


class CustomStrategies:
    """
    Clase que contiene estrategias personalizadas
    """

    @staticmethod
    def strategy_dual_position(symbol, volume=0.1, trend_limit=True, logger=None, debug_mode=False):
        """
        Estrategia
        """

        # Conexión a MT5
        if not mt5.initialize():
            if logger:
                logger.error("Error al inicializar MT5 en strategy_dual_position")
            return
        

        

            # Cerrar todas las posiciones al finalizar
            if logger:
                logger.log("🔒 Finalizando estrategia - cerrando todas las posiciones...")
            
            current_positions = mt5.positions_get(symbol=symbol)
            if current_positions:
                for pos in current_positions:
                    close_position(pos.ticket, "Finalizacion estrategia")
            
            CustomStrategies._strategy_dual_position_running = False
            CustomStrategies._strategy_dual_position_finished = True
            if logger:
                logger.log("✅ strategy_dual_position finalizada")