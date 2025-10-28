import time
import math
from datetime import datetime, timedelta
import pandas as pd
import pandas_ta as ta
import numpy as np
from datetime import datetime


try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

class CustomStrategies:
    """
    Clase que contiene estrategias personalizadas
    """

    @staticmethod
    def strategy_scalping_m1(symbol, lot=0.1, entry_pct=0.05, exit_pct=0.5, n_bars=60, logger=None):
        """
        Función de scalping intradía en MT5 con timeframe 1 minuto.
        
        Parámetros:
        - symbol: string, par de divisas o instrumento (ej: "EURUSD")
        - lot: float, tamaño de lote
        - entry_pct: float, % de cambio desde apertura para entrar
        - exit_pct: float, % de ganancia para salir (no implementado stop-loss)
        - n_bars: int, número de velas M1 a analizar
        - logger: logger object para logging
        """

        # Conexión a MT5
        if not mt5.initialize():
            if logger:
                logger.error("Error al inicializar MT5 en strategy_scalping_m1")
            return
        if logger:
            logger.log("strategy_scalping_m1: Conectado a MT5")

        try:
            # Solo ejecutar UNA VEZ, no en bucle infinito
            if logger:
                logger.log(f"strategy_scalping_m1: Analizando {symbol} con {n_bars} velas")
            
            # 1️⃣ Obtener últimas n_bars de M1
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, n_bars)
            if rates is None:
                if logger:
                    logger.warn("strategy_scalping_m1: No se pudo obtener datos")
                return

            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df.set_index('time', inplace=True)

            if logger:
                logger.log(f"strategy_scalping_m1: Obtenidas {len(df)} velas")

            # 2️⃣ Señal de scalping
            open_price = df['open'].iloc[0]
            last_close = df['close'].iloc[-1]
            pct_change = (last_close - open_price) / open_price * 100

            if logger:
                logger.log(f"strategy_scalping_m1: Precio apertura: {open_price}, Último cierre: {last_close}, Cambio %: {pct_change:.4f}")

            signal = None
            if pct_change >= entry_pct:
                signal = "BUY"
            elif pct_change <= -entry_pct:
                signal = "SELL"

            if logger:
                logger.log(f"strategy_scalping_m1: Señal detectada: {signal}")

            # 3️⃣ Ejecutar orden si hay señal
            if signal:
                symbol_info = mt5.symbol_info(symbol)
                if symbol_info is None or not symbol_info.visible:
                    mt5.symbol_select(symbol, True)

                if signal == "BUY":
                    price = mt5.symbol_info_tick(symbol).ask
                    order_type = mt5.ORDER_TYPE_BUY
                else:
                    price = mt5.symbol_info_tick(symbol).bid
                    order_type = mt5.ORDER_TYPE_SELL

                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": symbol,
                    "volume": lot,
                    "type": order_type,
                    "price": price,
                    "deviation": 10,
                    "magic": 123456,
                    "comment": "scalping M1",
                    "type_filling": mt5.ORDER_FILLING_FOK
                }

                result = mt5.order_send(request)
                if logger:
                    logger.log(f"strategy_scalping_m1: {signal} ejecutado a {price}, resultado: {result}")
            else:
                if logger:
                    logger.log(f"strategy_scalping_m1: No hay señal. Cambio %: {pct_change:.4f} (umbral: ±{entry_pct})")

        except Exception as e:
            if logger:
                logger.error(f"strategy_scalping_m1: Error: {str(e)}")

        finally:
            # NO cerrar MT5 aquí porque otras partes del sistema lo usan
            if logger:
                logger.log("strategy_scalping_m1: Análisis completado")