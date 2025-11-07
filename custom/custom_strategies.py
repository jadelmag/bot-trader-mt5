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

    # @staticmethod
    # def strategy_dual_position(symbol, volume=0.01, trend_limit=True, logger=None, debug_mode=False):
    #     """
    #     Estrategia
    #     """
    #     # Conexión a MT5
    #     if not mt5.initialize():
    #         if logger:
    #             logger.error("Error al inicializar MT5 en strategy_dual_position")
    #         return
        
    #     # Obtenemos la última vela
    #     rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 1)

    #     open_price = 0
    #     close_price = 0
    #     if len(rates) == 1:
    #         open_price = rates[0]['open']
    #         close_price = rates[0]['close']

    #     logger.log(f"open_price: {open_price}")
    #     logger.log(f"close_price: {close_price}")

    #     ## Variables para análisis
    #     ticks_bid = []
    #     operation = 'neutral'
    #     profit = 0

    #     for var in range(1, 61):  # 60 segundos
    #         tick = mt5.symbol_info_tick(symbol)
    #         if tick is not None:
    #             ticks_bid.append(tick.bid)
    #             if debug_mode:
    #                 logger.log(f"Segundo: {var} | Bid: {tick.bid} | Ask: {tick.ask}")
    #         else:
    #             logger.warn("No se pudo obtener el tick.")
            
    #         # ---- Análisis a los 20 segundos ----
    #         if var == 40 and len(ticks_bid) > 1:
    #             start_price = ticks_bid[0]
    #             current_price = ticks_bid[-1]
    #             delta = current_price - start_price

    #             if delta > 0.00005:  # Subió más de 0.5 pip → LONG
    #                 operation = 'long'
    #             elif delta < -0.00005:  # Bajó más de 0.5 pip → SHORT
    #                 operation = 'short'
    #             else:
    #                 operation = 'neutral'

    #             logger.log(f"[{var}s] Movimiento detectado: {delta:.5f} → Operación sugerida: {operation.upper()}")

    #             if operation == 'long':
    #                 CustomStrategies.open_long_operation(symbol, volume, logger=logger)
    #             elif operation == 'short':
    #                 CustomStrategies.open_short_operation(symbol, volume, logger=logger)
    #             elif operation == 'neutral':
    #                 return
    #             break  # 👈 rompe el bucle a los 20 segundos

    #         time.sleep(1)

    @staticmethod
    def strategy_dual_position(symbol, volume=0.01, trend_limit=True, logger=None, debug_mode=False):
        """
        Estrategia
        """
        # Conexión a MT5
        if not mt5.initialize():
            if logger:
                logger.error("Error al inicializar MT5 en strategy_dual_position")
            return
        
        # Variables para análisis
        ticks_price = []
        operation = 'neutral'
        profit = 0

        for var in range(1, 61):  # 60 segundos
            tick = mt5.symbol_info_tick(symbol)
            current_price = (tick.bid + tick.ask) / 2
            if tick is not None:
                ticks_price.append(current_price)
                if debug_mode:
                    logger.log(f"Segundo: {var} | Precio: {current_price}")
            else:
                logger.warn("No se pudo obtener el tick.")
            
            # ---- Análisis a los 20 segundos ----
            if var == 40 and len(ticks_price) > 1:
                operation = CustomStrategies.detect_operation(ticks_price, logger=logger)
                
                if operation == 'long':
                    CustomStrategies.open_long_operation(symbol, volume, logger=logger)
                elif operation == 'short':
                    CustomStrategies.open_short_operation(symbol, volume, logger=logger)
                elif operation == 'neutral':
                    return
                break  # 👈 rompe el bucle a los 20 segundos

            time.sleep(1)

    @staticmethod
    def detect_operation(ticks_price, logger=None):
        """
        Analyzes real-time collected prices (ticks_price)
        and determines whether to open a LONG, SHORT, or stay NEUTRAL.
        """

        # Ensure there is enough data
        if len(ticks_price) < 5:
            if logger:
                logger.warn("Not enough data for analysis, staying neutral.")
            return "neutral"

        # Calculate general trend: difference between the current and the initial price
        initial_price = ticks_price[0]
        final_price = ticks_price[-1]
        change = final_price - initial_price

        # Calculate volatility (total range)
        max_price = max(ticks_price)
        min_price = min(ticks_price)
        price_range = max_price - min_price

        # Calculate average slope (trend in the last N ticks)
        window = min(10, len(ticks_price))  # last 10 ticks or fewer
        avg_recent = sum(ticks_price[-window:]) / window
        slope = final_price - avg_recent

        if logger:
            logger.log(f"📈 Initial price: {initial_price}")
            logger.log(f"📉 Final price:   {final_price}")
            logger.log(f"📊 Total change:  {change:.6f}")
            logger.log(f"📊 Range:         {price_range:.6f}")
            logger.log(f"📊 Slope (last {window} ticks): {slope:.6f}")

        # --- Decision based on thresholds ---
        trend_threshold = 0.00005      # ≈ 0.5 pips (adjust as needed)
        volatility_threshold = 0.00010 # ≈ 1 pip minimum movement

        if price_range < volatility_threshold:
            # Sideways market → no trade
            decision = "neutral"
        elif change > trend_threshold and slope > 0:
            # Price rising with positive slope → LONG
            decision = "long"
        elif change < -trend_threshold and slope < 0:
            # Price falling with negative slope → SHORT
            decision = "short"
        else:
            # No clear direction → wait
            decision = "neutral"

        if logger:
            logger.log(f"🧭 Trade decision: {decision.upper()}")

        return decision

    @staticmethod
    def open_long_operation(symbol, volume, sl_pips=20, tp_pips=30, logger=None):
        """
        Abre una operación LONG
        """
        # Obtenemos el último tick
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            if logger:
                logger.error(f"❌ No se pudo obtener tick para {symbol}")
            return False

        # Calcular precios SL/TP (en función de pips)
        price_open = tick.ask
        point = mt5.symbol_info(symbol).point
        sl = price_open - sl_pips * point
        tp = price_open + tp_pips * point

        # Creamos la orden de compra
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": mt5.ORDER_TYPE_BUY,
            "price": price_open,
            "sl": sl,
            "tp": tp,
            "deviation": 20,
            "magic": 123456,
            "comment": "Apertura LONG automática",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_FOK,
        }

        # Enviar orden
        result = mt5.order_send(request)

        # Validar resultado
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            if logger:
                logger.error(f"❌ Error al abrir LONG: {result.comment}")

        if logger:
            logger.success(f"✅ Operación LONG abierta en {symbol} | Precio: {price_open:.5f} | SL: {sl:.5f} | TP: {tp:.5f}")  

        for var in range(1, 61):
            profit = CustomStrategies.check_generate_profit(symbol, logger)
            logger.log(f"Profit: {profit}")
            
            if profit is not None and profit > 0:
                logger.success(f"✅ Beneficio total actual: +{profit:.2f} USD")
                CustomStrategies.close_operation(None, logger)
                break
            
            time.sleep(1)
         
    @staticmethod
    def open_short_operation(symbol, volume, sl_pips=20, tp_pips=30, logger=None):
        """
        Abre una operación SHORT
        """
        # Obtenemos el último tick
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            if logger:
                logger.error(f"❌ No se pudo obtener tick para {symbol}")
            return False

        # Calcular precios SL/TP (en función de pips) - Para SHORT
        price_open = tick.bid  # Para SHORT usamos bid
        point = mt5.symbol_info(symbol).point
        sl = price_open + sl_pips * point  # Para SHORT, SL está arriba
        tp = price_open - tp_pips * point  # Para SHORT, TP está abajo

        # Creamos la orden de venta
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": mt5.ORDER_TYPE_SELL,
            "price": price_open,
            "sl": sl,
            "tp": tp,
            "deviation": 20,
            "magic": 123456,
            "comment": "Apertura SHORT automática",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_FOK,
        }

        # Enviar orden
        result = mt5.order_send(request)

        # Validar resultado
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            if logger:
                logger.error(f"❌ Error al abrir SHORT: {result.comment}")

        if logger:
            logger.success(f"✅ Operación SHORT abierta en {symbol} | Precio: {price_open:.5f} | SL: {sl:.5f} | TP: {tp:.5f}")


        for var in range(1, 61):
            profit = CustomStrategies.check_generate_profit(symbol, logger)
            logger.log(f"Profit: {profit}")
            
            if profit is not None and profit > 0:
                logger.success(f"✅ Beneficio total actual: +{profit:.2f} USD")
                CustomStrategies.close_operation(None, logger)
                break
            
            time.sleep(1)

    @staticmethod
    def check_generate_profit(symbol=None, logger=None):
        """
        Verifica si hay operaciones abiertas y determina si generan beneficio o pérdida.
        Si se pasa un símbolo, solo analiza ese; si no, analiza todas las operaciones abiertas.
        """

        # Asegurar conexión
        if not mt5.initialize():
            if logger:
                logger.error("Error al inicializar MT5 en check_generate_profit")
            return None

        # Obtener todas las posiciones abiertas
        positions = mt5.positions_get(symbol=symbol)
        if positions is None or len(positions) == 0:
            if logger:
                logger.log("ℹ️ No hay operaciones abiertas.")
            return None

        total_profit = 0.0

        for pos in positions:
            symbol = pos.symbol
            profit = pos.profit
            price_open = pos.price_open
            volume = pos.volume
            ticket = pos.ticket

            total_profit += profit

            # Log por operación
            if logger:
                status = "🟢 GANANCIA" if profit > 0 else "🔴 PÉRDIDA"
                logger.log(f"[{symbol}] Ticket: {ticket} | Vol: {volume} | Open: {price_open:.5f} | Profit: {profit:.2f} USD → {status}")

        # Log general
        if logger:
            if total_profit > 0:
                logger.log(f"✅ Beneficio total actual: +{total_profit:.2f} USD")
            else:
                logger.log(f"❌ Pérdida total actual: {total_profit:.2f} USD")

        return total_profit

    @staticmethod
    def close_operation(ticket=None, logger=None):
        """
        Cierra una operación abierta en MetaTrader 5.
        Si no se pasa un ticket, cierra todas las operaciones abiertas.
        """
        # Asegurar conexión
        if not mt5.initialize():
            if logger:
                logger.error("❌ Error al inicializar MT5 en close_operation()")
            return False

        # Obtener las posiciones abiertas
        if ticket:
            positions = [pos for pos in mt5.positions_get() if pos.ticket == ticket]
        else:
            positions = mt5.positions_get()

        if not positions or len(positions) == 0:
            if logger:
                logger.log("ℹ️ No hay operaciones abiertas para cerrar.")
            return False

        for pos in positions:
            symbol = pos.symbol
            position_ticket = pos.ticket
            volume = pos.volume
            order_type = pos.type  # 0=BUY, 1=SELL

            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                if logger:
                    logger.error(f"❌ No se pudo obtener tick para {symbol}")
                continue

            # Determinar tipo de operación inversa para cerrar
            if order_type == mt5.ORDER_TYPE_BUY:
                price = tick.bid  # cierre de compra al BID
                order_type_close = mt5.ORDER_TYPE_SELL
            else:
                price = tick.ask  # cierre de venta al ASK
                order_type_close = mt5.ORDER_TYPE_BUY

            close_request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": order_type_close,
                "position": position_ticket,
                "price": price,
                "deviation": 20,
                "magic": 123456,
                "comment": "Cierre automático de operación",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_FOK,
            }

            result = mt5.order_send(close_request)

            if result.retcode == mt5.TRADE_RETCODE_DONE:
                if logger:
                    logger.success(f"✅ Operación cerrada correctamente | Ticket: {position_ticket} | {symbol} | Precio cierre: {price:.5f}")
            else:
                if logger:
                    logger.error(f"❌ Error al cerrar operación {position_ticket}: {result.comment}")

        return True
