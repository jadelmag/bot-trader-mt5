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
    def strategy_dual_position(symbol, volume=0.1, trend_close=False, trend_limit=True, logger=None):
        """
        Estrategia de hedging que abre posiciones simultáneas LONG y SHORT al inicio de cada nueva vela.
        
        Parámetros:
        - symbol: string, par de divisas o instrumento (ej: "EURUSD")
        - volume: float, tamaño de lote para cada posición
        - trend_close: bool, si se cierra la operacion cuando el precio de la vela empieza a bajar
        - trend_limit: bool, si se cierra la operacion cuando el precio llega al limite PL
        - logger: logger object para logging
        
        Lógica:
        1. Al inicio de cada nueva vela, abre LONG y SHORT simultáneamente
        2. Posición ganadora se cierra por: tendencia inversa (si trend_close=True) O límite de beneficio (si trend_limit=True)
        3. Posición perdedora se cierra cuando llega a cero (stop loss máximo)
        """
        
        # Conexión a MT5
        if not mt5.initialize():
            if logger:
                logger.error("Error al inicializar MT5 en strategy_dual_position")
            return
        
        # Cargar configuración para obtener close_custom_limit
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'strategies', 'config.json')
        close_custom_limit = 50.0  # Valor por defecto
        
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                close_custom_limit = float(config.get('close_custom_limit', 50.0))
        except Exception as e:
            if logger:
                logger.warning(f"No se pudo cargar config.json, usando valor por defecto: {e}")
        
        if logger:
            logger.log(f"strategy_dual_position: Iniciando estrategia para {symbol}")
            logger.log(f"Parámetros: volume={volume}, trend_close={trend_close}, trend_limit={trend_limit}")
            logger.log(f"Límite de beneficio (close_custom_limit): {close_custom_limit}")
        
        # Variables de control
        active_positions = {}  # {ticket: {'type': 'LONG'/'SHORT', 'open_price': float, 'open_time': datetime}}
        last_candle_time = None
        running = True
        
        def get_current_price():
            """Obtiene el precio actual del símbolo"""
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                return None
            return (tick.bid + tick.ask) / 2
        
        def get_candle_data():
            """Obtiene datos de la última vela"""
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 2)
            if rates is None or len(rates) < 2:
                return None, None
            return rates[-1], rates[-2]  # current, previous
        
        def open_dual_positions(current_price):
            """Abre posiciones LONG y SHORT simultáneamente"""
            positions_opened = []
            
            # Abrir posición LONG
            long_request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": mt5.ORDER_TYPE_BUY,
                "price": mt5.symbol_info_tick(symbol).ask,
                "deviation": 20,
                "magic": 234000,
                "comment": "Custom_Hedging_LONG",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_FOK,
            }
            
            long_result = mt5.order_send(long_request)
            if long_result and long_result.retcode == mt5.TRADE_RETCODE_DONE:
                positions_opened.append({
                    'ticket': long_result.order,
                    'type': 'LONG',
                    'open_price': long_result.price,
                    'open_time': datetime.now()
                })
                if logger:
                    logger.log(f"✅ LONG abierta - Ticket: {long_result.order}, Precio: {long_result.price}, Volumen: {volume}")
            else:
                if long_result:
                    logger.error(f"❌ Error abriendo LONG: {long_result.retcode} - {long_result.comment}")
                else:
                    logger.error(f"❌ Error abriendo LONG: mt5.order_send devolvió None. last_error={mt5.last_error()}")
            
            # Abrir posición SHORT
            short_request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": mt5.ORDER_TYPE_SELL,
                "price": mt5.symbol_info_tick(symbol).bid,
                "deviation": 20,
                "magic": 234000,
                "comment": "Custom_Hedging_SHORT",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_FOK,
            }
            
            short_result = mt5.order_send(short_request)
            if short_result and short_result.retcode == mt5.TRADE_RETCODE_DONE:
                positions_opened.append({
                    'ticket': short_result.order,
                    'type': 'SHORT',
                    'open_price': short_result.price,
                    'open_time': datetime.now()
                })
                if logger:
                    logger.log(f"✅ SHORT abierta - Ticket: {short_result.order}, Precio: {short_result.price}, Volumen: {volume}")
            else:
                if short_result:
                    logger.error(f"❌ Error abriendo SHORT: {short_result.retcode} - {short_result.comment}")
                else:
                    logger.error(f"❌ Error abriendo SHORT: mt5.order_send devolvió None. last_error={mt5.last_error()}")
            
            return positions_opened
        
        def close_position(ticket, reason=""):
            """Cierra una posición específica"""
            positions = mt5.positions_get(ticket=ticket)
            if not positions:
                return False
            
            position = positions[0]
            
            # Determinar tipo de orden de cierre
            if position.type == mt5.POSITION_TYPE_BUY:
                order_type = mt5.ORDER_TYPE_SELL
                price = mt5.symbol_info_tick(symbol).bid
            else:
                order_type = mt5.ORDER_TYPE_BUY
                price = mt5.symbol_info_tick(symbol).ask
            
            close_request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": position.volume,
                "type": order_type,
                "position": ticket,
                "price": price,
                "deviation": 20,
                "magic": 234000,
                "comment": f"Close_{reason}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_FOK,
            }
            
            result = mt5.order_send(close_request)
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                profit = position.profit
                position_type = "LONG" if position.type == mt5.POSITION_TYPE_BUY else "SHORT"
                if logger:
                    logger.log(f"🔒 {position_type} cerrada - Ticket: {ticket}, P/L: {profit:.2f}, Razón: {reason}")
                return True
            else:
                if result:
                    logger.error(f"❌ Error cerrando posición {ticket}: {result.retcode} - {result.comment}")
                else:
                    logger.error(f"❌ Error cerrando posición {ticket}: mt5.order_send devolvió None. last_error={mt5.last_error()}")
                return False
        
        def check_trend_reversal(current_candle, previous_candle):
            """Detecta cambio de tendencia basado en el movimiento de precios"""
            if current_candle is None or previous_candle is None:
                return False
            
            # Detectar si el precio está empezando a bajar (tendencia inversa)
            # Para LONG: si el precio actual es menor que el anterior (bajando)
            # Para SHORT: si el precio actual es mayor que el anterior (subiendo)
            current_close = current_candle['close']
            previous_close = previous_candle['close']
            
            # Retorna True si hay un cambio significativo de tendencia
            return abs(current_close - previous_close) > 0.0001  # Cambio mínimo de 1 pip
        
        def monitor_positions():
            """Monitorea las posiciones activas y aplica lógica de cierre"""
            nonlocal active_positions
            
            current_positions = mt5.positions_get(symbol=symbol)
            if not current_positions:
                active_positions.clear()
                return
            
            # Actualizar posiciones activas
            current_tickets = {pos.ticket for pos in current_positions}
            active_positions = {ticket: data for ticket, data in active_positions.items() 
                              if ticket in current_tickets}
            
            # Añadir nuevas posiciones si no están en el tracking
            for pos in current_positions:
                if pos.ticket not in active_positions:
                    pos_type = "LONG" if pos.type == mt5.POSITION_TYPE_BUY else "SHORT"
                    active_positions[pos.ticket] = {
                        'type': pos_type,
                        'open_price': pos.price_open,
                        'open_time': datetime.fromtimestamp(pos.time)
                    }
            
            # Obtener datos de velas para detectar cambio de tendencia
            current_candle, previous_candle = get_candle_data()
            trend_reversed = check_trend_reversal(current_candle, previous_candle)
            
            positions_to_close = []
            
            for pos in current_positions:
                # Verificar si es posición ganadora (profit > 0)
                if pos.profit > 0:
                    should_close = False
                    close_reason = ""
                    
                    # Cerrar por límite de beneficio (solo si trend_limit está activo)
                    if trend_limit and pos.profit >= close_custom_limit:
                        should_close = True
                        close_reason = f"Límite_beneficio_{pos.profit:.2f}"
                    
                    # Cerrar por cambio de tendencia (solo si trend_close está activo)
                    elif trend_close and trend_reversed:
                        # Verificar dirección específica de la posición
                        current_candle, previous_candle = get_candle_data()
                        if current_candle and previous_candle:
                            current_price = current_candle['close']
                            previous_price = previous_candle['close']
                            
                            # Para posición LONG: cerrar si el precio empieza a bajar
                            if pos.type == mt5.POSITION_TYPE_BUY and current_price < previous_price:
                                should_close = True
                                close_reason = f"Tendencia_bajista_{pos.profit:.2f}"
                            
                            # Para posición SHORT: cerrar si el precio empieza a subir
                            elif pos.type == mt5.POSITION_TYPE_SELL and current_price > previous_price:
                                should_close = True
                                close_reason = f"Tendencia_alcista_{pos.profit:.2f}"
                    
                    if should_close:
                        positions_to_close.append((pos.ticket, close_reason))
                
                # Verificar si es posición perdedora que llegó cerca de cero
                elif pos.profit <= -0.95 * (pos.volume * 100000 * 0.0001):  # Aproximadamente en cero
                    positions_to_close.append((pos.ticket, f"Stop_loss_cero_{pos.profit:.2f}"))
            
            # Cerrar posiciones marcadas
            for ticket, reason in positions_to_close:
                if close_position(ticket, reason):
                    if ticket in active_positions:
                        del active_positions[ticket]
        
        def strategy_loop():
            """Bucle principal de la estrategia"""
            nonlocal last_candle_time, running
            
            while running:
                try:
                    # Obtener datos de vela actual
                    current_candle, _ = get_candle_data()
                    if current_candle is None:
                        time.sleep(1)
                        continue
                    
                    current_time = datetime.fromtimestamp(current_candle['time'])
                    
                    # Verificar si es una nueva vela
                    if last_candle_time is None or current_time > last_candle_time:
                        last_candle_time = current_time
                        
                        # Solo abrir nuevas posiciones si no hay posiciones activas
                        current_positions = mt5.positions_get(symbol=symbol)
                        if not current_positions:
                            current_price = get_current_price()
                            if current_price:
                                if logger:
                                    logger.log(f"📊 Nueva vela detectada - {current_time.strftime('%H:%M:%S')} - Precio: {current_price}")
                                
                                new_positions = open_dual_positions(current_price)
                                for pos_data in new_positions:
                                    active_positions[pos_data['ticket']] = pos_data
                    
                    # Monitorear posiciones existentes
                    monitor_positions()
                    
                    # Pausa antes del siguiente ciclo
                    time.sleep(1)
                    
                except Exception as e:
                    if logger:
                        logger.error(f"Error en strategy_loop: {str(e)}")
                    time.sleep(5)
        
        # Iniciar la estrategia en un hilo separado
        if logger:
            logger.log("🚀 Iniciando strategy_hedging_dual_position...")
        
        try:
            strategy_thread = threading.Thread(target=strategy_loop, daemon=True)
            strategy_thread.start()
            
            # Mantener el hilo principal activo
            while running:
                time.sleep(10)
                
        except KeyboardInterrupt:
            if logger:
                logger.log("⏹️ Deteniendo strategy_hedging_dual_position...")
            running = False
        
        finally:
            # Cerrar todas las posiciones al finalizar
            current_positions = mt5.positions_get(symbol=symbol)
            if current_positions:
                if logger:
                    logger.log("🔒 Cerrando todas las posiciones al finalizar...")
                for pos in current_positions:
                    close_position(pos.ticket, "Finalizacion_estrategia")
            
            mt5.shutdown()
            if logger:
                logger.log("✅ strategy_hedging_dual_position finalizada")