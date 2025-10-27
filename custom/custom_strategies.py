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
    def strategy_pico_y_pala(df):
        """
        Estrategia de pico y pala basada en velas
        """
        body_size = abs(df['close'] - df['open'])
        range_size = df['high'] - df['low']

        # Evitamos división por cero
        if range_size == 0:
            return None

        # Si el cuerpo es más del 60% del rango total → señal fuerte
        if body_size / range_size > 0.6:
            if df['close'] > df['open']:
                return "long"
            elif df['open'] > df['close']:
                return "short"
        return None

    @staticmethod
    def run_pico_y_pala(simulation_instance, symbol: str, volume: float, logger=None, threshold_pips: float = 1.0):
        """
        Estrategia de scalping modificada basada en ticks.
        1. Esperar a que se forme una vela nueva y obtener el precio de cierre
        2. Esperar 10 ticks y contar cuántos son mayores/menores al precio de referencia
        3. Abrir operación según el resultado
        """

        # --- Comprobación de operación existente ---
        open_positions = mt5.positions_get(symbol=symbol)
        if open_positions:
            for pos in open_positions:
                if pos.comment == "custom Pico y Pala":
                    if logger: logger.log("[PICO Y PALA] Ya existe una operación de esta estrategia. No se abrirá una nueva.")
                    return

        if not mt5:
            if logger:
                logger.error("[PICO Y PALA] MT5 no está disponible.")
            return

        # --- Fase 1: Esperar vela nueva y obtener precio de cierre ---
        if logger: logger.log("[PICO Y PALA] Esperando nueva vela M1...")
        
        # Obtener la última vela completa
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 1)
        if rates is None or len(rates) == 0:
            if logger: logger.error("[PICO Y PALA] No se pudieron obtener datos de velas M1.")
            return
        
        initial_close_price = rates[0]['close']
        if logger: logger.log(f"[PICO Y PALA] Precio de cierre de referencia: {initial_close_price} $")

        # --- Fase 2: Recopilar 10 ticks y comparar con el precio de referencia ---
        if logger: logger.log("[PICO Y PALA] Recopilando 10 ticks...")
        
        ticks_data = []
        tick_count = 0
        max_ticks = 10
        
        while tick_count < max_ticks:
            # --- MODIFICACIÓN PARA SIMULACIÓN ---
            # En lugar de un tick real, usamos el precio de cierre actual de la simulación.
            # Esto asume que el precio no cambia drásticamente en los pocos segundos que dura la recogida de ticks.
            if simulation_instance.current_candle:
                current_price = simulation_instance.current_candle['close']
                current_time_unix = int(time.time())
            else:
                # Fallback por si la vela actual no está disponible
                time.sleep(0.1)
                continue

            if current_time_unix > rates[0]['time']:
                ticks_data.append(current_price)
                tick_count += 1
                if logger: logger.log(f"[PICO Y PALA] Tick simulado {tick_count}/{max_ticks}: {current_price}")
            
            time.sleep(0.1)  # Pequeña pausa para simular el paso del tiempo

        # --- Fase 3: Calcular ticks mayores/menores al precio de referencia ---
        ticks_above = sum(1 for tick_price in ticks_data if tick_price > initial_close_price)
        ticks_below = sum(1 for tick_price in ticks_data if tick_price < initial_close_price)
        
        if logger: logger.log(f"[PICO Y PALA] Resultados - Ticks arriba: {ticks_above}, Ticks abajo: {ticks_below}")

        # --- Fase 4: Determinar dirección de la operación ---
        if ticks_above > ticks_below:
            direction = 'long'
            if logger: logger.log(f"[PICO Y PALA] Señal LONG (más ticks arriba: {ticks_above} vs {ticks_below})")
        elif ticks_below > ticks_above:
            direction = 'short'
            if logger: logger.log(f"[PICO Y PALA] Señal SHORT (más ticks abajo: {ticks_below} vs {ticks_above})")
        else:
            if logger: logger.warn("[PICO Y PALA] Empate en ticks. No se opera.")
            return

        # --- Fase 5: Abrir operación ---
        result = simulation_instance.open_trade(
            trade_type=direction, 
            symbol=symbol, 
            volume=volume, 
            sl_pips=50, 
            tp_pips=0,
            strategy_name="custom Pico y Pala"
        )
        
        if not result or result.retcode != mt5.TRADE_RETCODE_DONE:
            if logger: logger.error("[PICO Y PALA] No se pudo abrir la operación.")
            return

        position_ticket = result.order
        if logger: logger.log(f"[PICO Y PALA] Operación {direction.upper()} abierta (Ticket: {position_ticket}). Gestionando...")

        # --- Fase 6: Gestión de la operación ---
        if direction == 'long':
            manage_long_position(simulation_instance, position_ticket, volume, initial_close_price, logger)
        else:
            manage_short_position(simulation_instance, position_ticket, volume, initial_close_price, logger)

    @staticmethod
    def manage_long_position(simulation_instance, position_ticket: int, volume: float, reference_price: float, logger=None):
        """
        Gestiona operación LONG:
        1. Intentar cerrar con mayor beneficio posible
        2. Sino, cerrar con menor beneficio posible
            """
        if logger: logger.log("[PICO Y PALA LONG] Iniciando gestión LONG...")
        
        max_profit_price = reference_price
        min_profit_price = reference_price
        ticks_without_improvement = 0
        max_ticks_without_improvement = 5
        
        while True:
            current_tick = mt5.symbol_info_tick(simulation_instance.symbol)
            if not current_tick:
                continue
            
            current_price = current_tick.last
            
            # Actualizar máximo beneficio
            if current_price > max_profit_price:
                max_profit_price = current_price
                ticks_without_improvement = 0
                if logger: logger.log(f"[PICO Y PALA LONG] Nuevo máximo: {max_profit_price}")
            else:
                ticks_without_improvement += 1
            
            # Estrategia 1: Cerrar con mayor beneficio posible
            # Si el precio baja un 30% desde el máximo alcanzado, cerramos
            drawdown_from_peak = ((max_profit_price - current_price) / max_profit_price) * 10000  # en pips aproximados
            
            if drawdown_from_peak >= 3.0:  # 3 pips de drawdown desde el pico
                context_msg = f"Cierre por drawdown desde pico ({drawdown_from_peak:.2f} pips)."
                simulation_instance.close_trade(position_ticket, volume, 'long', strategy_context=context_msg)
                return
            
            # Estrategia 2: Cierre por tiempo/condición secundaria
            if ticks_without_improvement >= max_ticks_without_improvement:
                context_msg = f"Cierre por falta de mejora ({ticks_without_improvement} ticks)."
                simulation_instance.close_trade(position_ticket, volume, 'long', strategy_context=context_msg)
                return
            
            time.sleep(0.5)  # Esperar medio segundo entre comprobaciones

    @staticmethod
    def manage_short_position(simulation_instance, position_ticket: int, volume: float, reference_price: float, logger=None):
        """
        Gestiona operación SHORT:
        1. Intentar cerrar con mayor beneficio posible
        2. Sino, cerrar con menor beneficio posible
        """
        if logger: logger.log("[PICO Y PALA SHORT] Iniciando gestión SHORT...")
        
        max_profit_price = reference_price  # Para short, el mejor precio es el más bajo
        min_profit_price = reference_price
        ticks_without_improvement = 0
        max_ticks_without_improvement = 5
        
        while True:
            current_tick = mt5.symbol_info_tick(simulation_instance.symbol)
            if not current_tick:
                continue
            
            current_price = current_tick.last
            
            # Actualizar máximo beneficio (para short, precio más bajo es mejor)
            if current_price < max_profit_price:
                max_profit_price = current_price
                ticks_without_improvement = 0
                if logger: logger.log(f"[PICO Y PALA SHORT] Nuevo mínimo: {max_profit_price}")
            else:
                ticks_without_improvement += 1
            
            # Estrategia 1: Cerrar con mayor beneficio posible
            # Si el precio sube un 30% desde el mínimo alcanzado, cerramos
            drawdown_from_peak = ((current_price - max_profit_price) / max_profit_price) * 10000  # en pips aproximados
            
            if drawdown_from_peak >= 3.0:  # 3 pips de drawdown desde el pico
                context_msg = f"Cierre por drawdown desde pico ({drawdown_from_peak:.2f} pips)."
                simulation_instance.close_trade(position_ticket, volume, 'short', strategy_context=context_msg)
                return
            
            # Estrategia 2: Cierre por tiempo/condición secundaria
            if ticks_without_improvement >= max_ticks_without_improvement:
                context_msg = f"Cierre por falta de mejora ({ticks_without_improvement} ticks)."
                simulation_instance.close_trade(position_ticket, volume, 'short', strategy_context=context_msg)
                return
            
            time.sleep(0.5)  # Esperar medio segundo entre comprobaciones

    

