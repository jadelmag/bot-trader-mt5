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
        

        

