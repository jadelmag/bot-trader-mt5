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

    _strategy_dual_position_running = False
    _strategy_dual_position_finished = False

    @classmethod
    def is_strategy_dual_position_running(cls):
        """Verifica si strategy_dual_position está ejecutándose"""
        return cls._strategy_dual_position_running and not cls._strategy_dual_position_finished
    
    @classmethod
    def reset_strategy_dual_position_status(cls):
        """Resetea el estado de strategy_dual_position"""
        cls._strategy_dual_position_running = False
        cls._strategy_dual_position_finished = False

    @staticmethod
    def strategy_dual_position(symbol, volume=0.1, trend_limit=True, logger=None, debug_mode=False):
        """
        Estrategia de hedging optimizada que abre posiciones simultáneas LONG y SHORT.
        
        Características:
        - Operaciones de larga duración (meses)
        - Sistema de tracking de pares optimizado
        - Cierre inteligente: ganadora por límite, perdedora cuando llega a cero
        - Una operación se cierra cuando llega a close_custom_limit
        - Su par se cierra cuando llega a pérdida cercana a cero
        - Lectura dinámica de configuración sin necesidad de reiniciar
        """

        # Marcar como ejecutándose
        CustomStrategies._strategy_dual_position_running = True
        CustomStrategies._strategy_dual_position_finished = False
        
        # Conexión a MT5
        if not mt5.initialize():
            if logger:
                logger.error("Error al inicializar MT5 en strategy_dual_position")
            return
        
        # Cargar configuración inicial
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'strategies', 'config.json')
        close_custom_limit = 200.0  # Valor por defecto aumentado
        
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                close_custom_limit = float(config.get('close_custom_limit', 200.0))
        except Exception as e:
            if logger:
                logger.warning(f"No se pudo cargar config.json, usando valor por defecto: {e}")
        
        if logger:
            logger.log(f"🚀 strategy_dual_position: Iniciando para {symbol}")
            logger.log(f"📊 Parámetros: volume={volume}, límite_beneficio={close_custom_limit}")
        
        # Variables de control optimizadas
        position_pairs = {}  # {pair_id: {'long_ticket': int, 'short_ticket': int, 'open_time': datetime, 'candle_time': datetime}}
        last_candle_time = None
        running = True
        pair_counter = 0
        
        def reload_config():
            """Recarga la configuración desde el archivo JSON"""
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    return float(config.get('close_custom_limit', 200.0))
            except Exception as e:
                if logger:
                    logger.warning(f"Error recargando config: {e}")
                return close_custom_limit  # Devolver valor actual si hay error
        
        def get_candle_data():
            """Obtiene datos de la última vela"""
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 2)
            if rates is None or len(rates) < 2:
                return None, None
            return rates[-1], rates[-2]
        
        def open_hedging_pair():
            """Abre un par de posiciones LONG y SHORT simultáneamente"""
            nonlocal pair_counter
            pair_counter += 1
            
            # Obtener precios actuales
            tick = mt5.symbol_info_tick(symbol)
            if not tick:
                if logger:
                    logger.error("No se pudo obtener tick del símbolo")
                return None
            
            # Crear requests para ambas posiciones
            long_request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": mt5.ORDER_TYPE_BUY,
                "price": tick.ask,
                "deviation": 20,
                "magic": 234000 + pair_counter,
                "comment": f"Hedge_LONG_P{pair_counter}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_FOK,
            }
            
            short_request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": mt5.ORDER_TYPE_SELL,
                "price": tick.bid,
                "deviation": 20,
                "magic": 234000 + pair_counter,
                "comment": f"Hedge_SHORT_P{pair_counter}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_FOK,
            }
            
            # Ejecutar órdenes
            long_result = mt5.order_send(long_request)
            short_result = mt5.order_send(short_request)
            
            # Verificar resultados
            long_ticket = None
            short_ticket = None
            
            if long_result and long_result.retcode == mt5.TRADE_RETCODE_DONE:
                long_ticket = long_result.order
                if logger:
                    logger.log(f"✅ LONG abierta - Par {pair_counter} | Ticket: {long_ticket} | Precio: {long_result.price:.5f} | Vol: {volume}")
            else:
                if logger:
                    error_msg = long_result.comment if long_result else "Error desconocido"
                    logger.error(f"❌ Error abriendo LONG Par {pair_counter}: {error_msg}")
            
            if short_result and short_result.retcode == mt5.TRADE_RETCODE_DONE:
                short_ticket = short_result.order
                if logger:
                    logger.log(f"✅ SHORT abierta - Par {pair_counter} | Ticket: {short_ticket} | Precio: {short_result.price:.5f} | Vol: {volume}")
            else:
                if logger:
                    error_msg = short_result.comment if short_result else "Error desconocido"
                    logger.error(f"❌ Error abriendo SHORT Par {pair_counter}: {error_msg}")
            
            # Si ambas se abrieron correctamente, guardar el par
            if long_ticket and short_ticket:
                pair_data = {
                    'long_ticket': long_ticket,
                    'short_ticket': short_ticket,
                    'open_time': datetime.now(),
                    'candle_time': last_candle_time,
                    'volume': volume
                }
                position_pairs[pair_counter] = pair_data
                
                if logger:
                    logger.log(f"🔗 Par {pair_counter} creado exitosamente - LONG: {long_ticket}, SHORT: {short_ticket}")
                
                return pair_counter
            else:
                # Si alguna falló, cerrar la que se abrió
                if long_ticket:
                    close_position(long_ticket, "Error_par_incompleto")
                if short_ticket:
                    close_position(short_ticket, "Error_par_incompleto")
                return None
        
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
                pos_type = "LONG"
            else:
                order_type = mt5.ORDER_TYPE_BUY
                price = mt5.symbol_info_tick(symbol).ask
                pos_type = "SHORT"
            
            close_request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": position.volume,
                "type": order_type,
                "position": ticket,
                "price": price,
                "deviation": 20,
                "magic": position.magic,
                "comment": f"Close_{reason}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_FOK,
            }
            
            result = mt5.order_send(close_request)
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                if logger:
                    logger.log(f"🔒 {pos_type} cerrada - Ticket: {ticket} | P/L: {position.profit:.2f} | Razón: {reason}")
                return True
            else:
                if logger:
                    error_msg = result.comment if result else "Error desconocido"
                    logger.error(f"❌ Error cerrando {pos_type} {ticket}: {error_msg}")
                return False
        
        def monitor_pairs():
            """Monitorea todos los pares de posiciones activos"""
            nonlocal position_pairs
            
            # Obtener todas las posiciones actuales
            current_positions = mt5.positions_get(symbol=symbol)
            if not current_positions:
                return
            
            # Crear diccionario de posiciones por ticket para acceso rápido
            positions_by_ticket = {pos.ticket: pos for pos in current_positions}
            
            pairs_to_remove = []
            
            for pair_id, pair_data in position_pairs.items():
                long_ticket = pair_data['long_ticket']
                short_ticket = pair_data['short_ticket']
                
                # Verificar si ambas posiciones siguen abiertas
                long_pos = positions_by_ticket.get(long_ticket)
                short_pos = positions_by_ticket.get(short_ticket)
                
                # Si alguna ya no existe, remover el par del tracking
                if not long_pos or not short_pos:
                    pairs_to_remove.append(pair_id)
                    continue
                
                # Recargar configuración dinámicamente
                current_close_limit = reload_config()
                
                # Log si el límite cambió
                if not hasattr(monitor_pairs, 'last_limit'):
                    monitor_pairs.last_limit = current_close_limit
                elif monitor_pairs.last_limit != current_close_limit:
                    if logger:
                        logger.log(f"🔄 Límite actualizado: {monitor_pairs.last_limit} → {current_close_limit}")
                    monitor_pairs.last_limit = current_close_limit
                
                # Verificar condiciones de cierre
                long_profit = long_pos.profit
                short_profit = short_pos.profit
                
                # LÓGICA CORREGIDA: Cerrar INMEDIATAMENTE el par cuando una operación llega al límite
                
                # Verificar si alguna operación alcanza el límite de beneficio
                if long_profit >= current_close_limit or short_profit >= current_close_limit:
                    
                    # Determinar cuál es la ganadora
                    if long_profit >= current_close_limit:
                        winner_ticket, winner_profit, winner_type = long_ticket, long_profit, "LONG"
                        pair_ticket, pair_profit, pair_type = short_ticket, short_profit, "SHORT"
                    else:
                        winner_ticket, winner_profit, winner_type = short_ticket, short_profit, "SHORT"
                        pair_ticket, pair_profit, pair_type = long_ticket, long_profit, "LONG"
                    
                    if logger:
                        logger.log(f"🎯 Par {pair_id}: {winner_type} alcanzó límite de beneficio ({winner_profit:.2f})")
                    
                    # Cerrar operación ganadora primero
                    winner_closed = close_position(winner_ticket, f"Limite_beneficio_{winner_profit:.2f}")
                    
                    # INMEDIATAMENTE cerrar la operación par (sin importar si tiene beneficios o pérdidas)
                    if winner_closed:
                        # Pequeña pausa para que MT5 actualice su estado
                        time.sleep(0.1)
                        
                        current_positions_updated = mt5.positions_get(symbol=symbol)
                        pair_still_exists = any(pos.ticket == pair_ticket for pos in current_positions_updated) if current_positions_updated else False
                        
                        if pair_still_exists:
                            # Obtener información actualizada de la posición par
                            pair_position = None
                            for pos in current_positions_updated:
                                if pos.ticket == pair_ticket:
                                    pair_position = pos
                                    break
                            
                            if pair_position:
                                updated_pair_profit = pair_position.profit
                                # Cerrar la operación par INMEDIATAMENTE
                                if updated_pair_profit >= 0:
                                    close_position(pair_ticket, f"Par_cerrado_beneficio_{updated_pair_profit:.2f}")
                                else:
                                    close_position(pair_ticket, f"Par_cerrado_perdida_{updated_pair_profit:.2f}")
                            else:
                                if logger:
                                    logger.log(f"⚠️ {pair_type} {pair_ticket} no encontrada en posiciones actualizadas")
                        else:
                            if logger:
                                logger.log(f"⚠️ {pair_type} {pair_ticket} ya no existe, probablemente cerrada manualmente")
                    
                    pairs_to_remove.append(pair_id)
            
            # Remover pares cerrados del tracking
            for pair_id in pairs_to_remove:
                if pair_id in position_pairs:
                    del position_pairs[pair_id]
                    if logger:
                        logger.log(f"🗑️ Par {pair_id} removido del tracking")

        def strategy_loop():
            """Bucle principal de la estrategia"""
            nonlocal last_candle_time, running
            
            if logger:
                logger.log("🔄 Iniciando bucle de estrategia hedging...")
            
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
                        
                        if logger:
                            logger.log(f"📊 Nueva vela M1 detectada - {current_time.strftime('%H:%M:%S')} | Pares activos: {len(position_pairs)}")
                        
                        # Solo abrir nuevo par si NO hay pares activos (todas las operaciones están cerradas)
                        if len(position_pairs) == 0:
                            new_pair_id = open_hedging_pair()
                            if new_pair_id:
                                if logger:
                                    logger.log(f"🆕 Nuevo par {new_pair_id} abierto en vela {current_time.strftime('%H:%M:%S')} - No había pares activos")
                        else:
                            if logger:
                                logger.log(f"⏳ Esperando cierre de pares activos ({len(position_pairs)}) antes de abrir nuevo par")
                    
                    # Monitorear pares existentes
                    monitor_pairs()
                    
                    # Pausa antes del siguiente ciclo
                    time.sleep(1)
                    
                except Exception as e:
                    if logger:
                        logger.error(f"Error en strategy_loop: {str(e)}")
                    time.sleep(5)

        # Iniciar la estrategia
        try:
            if logger:
                logger.log("🚀 Iniciando strategy_dual_position optimizada...")
            
            strategy_thread = threading.Thread(target=strategy_loop, daemon=True)
            strategy_thread.start()
            
            # Mantener el hilo principal activo
            while running:
                time.sleep(10)
                
        except KeyboardInterrupt:
            if logger:
                logger.log("⏹️ Deteniendo strategy_dual_position...")
            running = False
        
        finally:
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