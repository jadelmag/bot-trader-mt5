import time
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

    @staticmethod
    def strategy_market_m1(df):
        """
        Función de análisis para EUR/USD en timeframe M1 usando pandas_ta
        Retorna señal: 1 (LONG), -1 (SHORT), 0 (NEUTRAL)
        """
        
        # Convertir datos si es necesario
        df = df.copy()
        df['Date'] = pd.to_datetime(df['Date'])
        df.set_index('Date', inplace=True)
        
        # Calcular indicadores técnicos con pandas_ta
        # Medias móviles
        df['SMA_5'] = ta.sma(df['Close'], length=5)
        df['SMA_10'] = ta.sma(df['Close'], length=10)
        df['SMA_20'] = ta.sma(df['Close'], length=20)
        
        # RSI
        df['RSI'] = ta.rsi(df['Close'], length=14)
        
        # MACD
        macd = ta.macd(df['Close'], fast=12, slow=26, signal=9)
        df = pd.concat([df, macd], axis=1)
        
        # Bollinger Bands
        bollinger = ta.bbands(df['Close'], length=20, std=2)
        df = pd.concat([df, bollinger], axis=1)
        
        # Estocástico
        stoch = ta.stoch(df['High'], df['Low'], df['Close'], k=14, d=3)
        df = pd.concat([df, stoch], axis=1)
        
        # ATR
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        
        # Ichimoku Cloud (opcional - buen indicador de tendencia)
        ichimoku = ta.ichimoku(df['High'], df['Low'], df['Close'])
        df = pd.concat([df, ichimoku[0]], axis=1)
        
        # Precio actual y velas anteriores
        precio_actual = df['Close'].iloc[-1]
        precio_anterior = df['Close'].iloc[-2] if len(df) > 1 else precio_actual
        
        # Señales individuales
        signals = {
            'tendencia_sma': 0,
            'momentum_rsi': 0,
            'macd': 0,
            'bollinger': 0,
            'stoch': 0,
            'patron_vela': 0,
            'ichimoku': 0
        }
        
        # 1. Señal de tendencia (Medias Móviles)
        if df['SMA_5'].iloc[-1] > df['SMA_10'].iloc[-1] > df['SMA_20'].iloc[-1]:
            signals['tendencia_sma'] = 1  # Tendencia alcista
        elif df['SMA_5'].iloc[-1] < df['SMA_10'].iloc[-1] < df['SMA_20'].iloc[-1]:
            signals['tendencia_sma'] = -1  # Tendencia bajista
        
        # 2. Señal RSI (sobrecompra/sobreventa)
        if df['RSI'].iloc[-1] < 30:
            signals['momentum_rsi'] = 1  # Posible rebote alcista
        elif df['RSI'].iloc[-1] > 70:
            signals['momentum_rsi'] = -1  # Posible corrección bajista
        
        # 3. Señal MACD
        if not pd.isna(df['MACD_12_26_9'].iloc[-1]) and not pd.isna(df['MACDs_12_26_9'].iloc[-1]):
            if df['MACD_12_26_9'].iloc[-1] > df['MACDs_12_26_9'].iloc[-1]:
                signals['macd'] = 1
            elif df['MACD_12_26_9'].iloc[-1] < df['MACDs_12_26_9'].iloc[-1]:
                signals['macd'] = -1
        
        # 4. Señal Bollinger Bands
        if not pd.isna(df['BBL_20_2.0'].iloc[-1]) and not pd.isna(df['BBU_20_2.0'].iloc[-1]):
            if precio_actual <= df['BBL_20_2.0'].iloc[-1]:
                signals['bollinger'] = 1  # Precio cerca del límite inferior
            elif precio_actual >= df['BBU_20_2.0'].iloc[-1]:
                signals['bollinger'] = -1  # Precio cerca del límite superior
        
        # 5. Señal Estocástico
        if not pd.isna(df['STOCHk_14_3_3'].iloc[-1]) and not pd.isna(df['STOCHd_14_3_3'].iloc[-1]):
            if df['STOCHk_14_3_3'].iloc[-1] < 20 and df['STOCHk_14_3_3'].iloc[-1] > df['STOCHd_14_3_3'].iloc[-1]:
                signals['stoch'] = 1
            elif df['STOCHk_14_3_3'].iloc[-1] > 80 and df['STOCHk_14_3_3'].iloc[-1] < df['STOCHd_14_3_3'].iloc[-1]:
                signals['stoch'] = -1
        
        # 6. Señal Ichimoku
        if not pd.isna(df['ISA_9'].iloc[-1]) and not pd.isna(df['ISB_26'].iloc[-1]):
            if precio_actual > df['ISA_9'].iloc[-1] and precio_actual > df['ISB_26'].iloc[-1]:
                signals['ichimoku'] = 1  # Por encima de la nube - alcista
            elif precio_actual < df['ISA_9'].iloc[-1] and precio_actual < df['ISB_26'].iloc[-1]:
                signals['ichimoku'] = -1  # Por debajo de la nube - bajista
        
        # 7. Patrones de velas
        cuerpo = abs(df['Close'].iloc[-1] - df['Open'].iloc[-1])
        rango_total = df['High'].iloc[-1] - df['Low'].iloc[-1]
        
        if cuerpo > 0 and rango_total > 0:
            ratio_cuerpo = cuerpo / rango_total
            # Vela alcista fuerte
            if df['Close'].iloc[-1] > df['Open'].iloc[-1] and ratio_cuerpo > 0.6:
                signals['patron_vela'] = 1
            # Vela bajista fuerte
            elif df['Close'].iloc[-1] < df['Open'].iloc[-1] and ratio_cuerpo > 0.6:
                signals['patron_vela'] = -1
        
        # Calcular señal final con pesos
        peso_total = sum([
            signals['tendencia_sma'] * 2,      # Mayor peso a tendencia
            signals['momentum_rsi'] * 1.5,
            signals['macd'] * 1.5,
            signals['bollinger'] * 1,
            signals['stoch'] * 1,
            signals['ichimoku'] * 1.5,         # Ichimoku tiene buen peso
            signals['patron_vela'] * 1
        ])
        
        # Umbrales para decisiones
        if peso_total >= 4:  # Umbral ligeramente más alto para mayor confianza
            return 1, signals, peso_total  # LONG
        elif peso_total <= -4:
            return -1, signals, peso_total  # SHORT
        else:
            return 0, signals, peso_total  # NEUTRAL

    @staticmethod
    def calcular_stop_loss_take_profit_pandasta(signal, precio_actual, atr):
        """
        Calcula Stop Loss y Take Profit basado en ATR
        """
        if signal == 1:  # LONG
            stop_loss = precio_actual - (atr * 1.5)
            take_profit = precio_actual + (atr * 2.5)
        elif signal == -1:  # SHORT
            stop_loss = precio_actual + (atr * 1.5)
            take_profit = precio_actual - (atr * 2.5)
        else:
            return None, None
        
        return stop_loss, take_profit

    @staticmethod
    def ejecutar_analisis_en_tiempo_real_pandasta(df_datos):
        """
        Función principal para usar en el bot de trading con pandas_ta
        """
        try:
            signal, signal_details, score = CustomStrategies.strategy_market_m1(df_datos)
            
            resultado = {
                'señal': signal,
                'puntuacion': score,
                'detalle_señales': signal_details,
                'timestamp': datetime.now(),
                'precio_actual': df_datos['Close'].iloc[-1]
            }
            
            # Si hay señal clara, calcular gestión de riesgo
            if signal != 0:
                atr_actual = df_datos['ATR'].iloc[-1] if 'ATR' in df_datos and not pd.isna(df_datos['ATR'].iloc[-1]) else 0.0005
                sl, tp = CustomStrategies.calcular_stop_loss_take_profit_pandasta(signal, resultado['precio_actual'], atr_actual)
                resultado['stop_loss'] = sl
                resultado['take_profit'] = tp
                
                # Calcular relación riesgo/recompensa
                if sl is not None and tp is not None:
                    riesgo = abs(resultado['precio_actual'] - sl)
                    recompensa = abs(tp - resultado['precio_actual'])
                    resultado['ratio_riesgo_recompensa'] = recompensa / riesgo if riesgo > 0 else 0
            
            return resultado
            
        except Exception as e:
            print(f"Error en análisis: {e}")
            return {
                'señal': 0,
                'puntuacion': 0,
                'error': str(e)
            }

    @staticmethod
    def manage_market_m1_position(simulation_instance, ticket: int, volume: float, direction: str, sl_pips: float, tp_pips: float, logger=None):
        """
        Monitorea una operación de Market M1 hasta que se cierre y registra el resultado
        """
        if logger:
            logger.log(f"[MARKET M1] Iniciando monitoreo de operación (Ticket: {ticket})")
        
        precio_apertura = None
        
        # Obtener precio de apertura
        try:
            positions = mt5.positions_get(ticket=ticket)
            if positions and len(positions) > 0:
                precio_apertura = positions[0].price_open
        except:
            pass
        
        # Monitorear hasta que la operación se cierre
        while True:
            try:
                # Verificar si la operación sigue abierta
                positions = mt5.positions_get(ticket=ticket)
                
                if not positions or len(positions) == 0:
                    # La operación se cerró
                    # Obtener información del historial
                    from_date = datetime.now() - timedelta(days=1)
                    deals = mt5.history_deals_get(position=ticket)
                    
                    if deals and len(deals) > 0:
                        # Encontrar el deal de cierre
                        close_deal = None
                        for deal in deals:
                            if deal.entry == 1:  # 1 = OUT (cierre)
                                close_deal = deal
                                break
                        
                        if close_deal:
                            profit = close_deal.profit
                            precio_cierre = close_deal.price
                            
                            # Determinar si cerró por SL o TP
                            motivo_cierre = "DESCONOCIDO"
                            if precio_apertura:
                                if direction == 'long':
                                    if profit > 0:
                                        motivo_cierre = "TAKE PROFIT"
                                    else:
                                        motivo_cierre = "STOP LOSS"
                                else:  # short
                                    if profit > 0:
                                        motivo_cierre = "TAKE PROFIT"
                                    else:
                                        motivo_cierre = "STOP LOSS"
                            
                            # Log detallado del cierre
                            if logger:
                                logger.log(f"[MARKET M1] ═══════════════════════════════════════")
                                logger.log(f"[MARKET M1] OPERACIÓN CERRADA (Ticket: {ticket})")
                                logger.log(f"[MARKET M1] Motivo: {motivo_cierre}")
                                logger.log(f"[MARKET M1] Dirección: {direction.upper()}")
                                logger.log(f"[MARKET M1] Volumen: {volume:.2f} lotes")
                                logger.log(f"[MARKET M1] SL configurado: {sl_pips:.1f} pips")
                                logger.log(f"[MARKET M1] TP configurado: {tp_pips:.1f} pips")
                                
                                if precio_apertura:
                                    logger.log(f"[MARKET M1] Precio apertura: {precio_apertura:.5f}")
                                    logger.log(f"[MARKET M1] Precio cierre: {precio_cierre:.5f}")
                                
                                if profit > 0:
                                    logger.log(f"[MARKET M1] ✅ BENEFICIOS: ${profit:.2f}")
                                else:
                                    logger.log(f"[MARKET M1] ❌ PÉRDIDAS: ${abs(profit):.2f}")
                                
                                logger.log(f"[MARKET M1] ═══════════════════════════════════════")
                    
                    break
                
                # Esperar 2 segundos antes de verificar de nuevo
                time.sleep(2)
                
            except Exception as e:
                if logger:
                    logger.error(f"[MARKET M1] Error monitoreando operación: {e}")
                break

    @staticmethod
    def run_market_m1(simulation_instance, symbol: str, volume: float, logger=None):
        """
        Estrategia de análisis técnico multi-indicador para M1
        Utiliza SMA, RSI, MACD, Bollinger Bands, Estocástico e Ichimoku
        """
        
        # Comprobación de operación existente
        open_positions = mt5.positions_get(symbol=symbol)
        if open_positions:
            for pos in open_positions:
                if pos.comment == "custom Market M1":
                    if logger: logger.log("[MARKET M1] Ya existe una operación de esta estrategia.")
                    return
        
        if not mt5:
            if logger:
                logger.error("[MARKET M1] MT5 no está disponible.")
            return
        
        # Obtener datos históricos (100 velas para calcular indicadores)
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 100)
        if rates is None or len(rates) < 50:
            if logger: logger.error("[MARKET M1] No se pudieron obtener suficientes datos históricos.")
            return
        
        # Convertir a DataFrame
        df = pd.DataFrame(rates)
        df['Date'] = pd.to_datetime(df['time'], unit='s')
        df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'tick_volume': 'Volume'}, inplace=True)
        
        try:
            # Ejecutar análisis usando la función de análisis existente
            resultado = CustomStrategies.ejecutar_analisis_en_tiempo_real_pandasta(df)
            
            if 'error' in resultado:
                if logger: logger.error(f"[MARKET M1] Error en análisis: {resultado['error']}")
                return
            
            señal = resultado['señal']
            puntuación = resultado['puntuacion']
            señales_detalle = resultado['detalle_señales']
            
            if logger:
                logger.log(f"[MARKET M1] Análisis completado - Señal: {señal}, Puntuación: {puntuación:.2f}")
                logger.log(f"[MARKET M1] Detalle señales: {señales_detalle}")
            
            # Si no hay señal clara, no operar
            if señal == 0:
                if logger: logger.log("[MARKET M1] Señal NEUTRAL - No se abre operación.")
                return
            
            # Determinar dirección
            direction = 'long' if señal == 1 else 'short'
            
            # Usar SL y TP ya calculados por ejecutar_analisis_en_tiempo_real_pandasta
            if 'stop_loss' in resultado and 'take_profit' in resultado:
                sl = resultado['stop_loss']
                tp = resultado['take_profit']
                precio_actual = resultado['precio_actual']
                
                # Convertir a pips
                sl_pips = abs(precio_actual - sl) * 10000
                tp_pips = abs(tp - precio_actual) * 10000
                
                if logger:
                    logger.log(f"[MARKET M1] Abriendo operación {direction.upper()}")
                    logger.log(f"[MARKET M1] SL: {sl_pips:.1f} pips, TP: {tp_pips:.1f} pips")
                    if 'ratio_riesgo_recompensa' in resultado:
                        logger.log(f"[MARKET M1] Ratio R/R: {resultado['ratio_riesgo_recompensa']:.2f}")
                
                # Abrir operación
                result = simulation_instance.open_trade(
                    trade_type=direction,
                    symbol=symbol,
                    volume=volume,
                    sl_pips=sl_pips,
                    tp_pips=tp_pips,
                    strategy_name="custom Market M1"
                )
                
                if not result or result.retcode != mt5.TRADE_RETCODE_DONE:
                    if logger: logger.error("[MARKET M1] No se pudo abrir la operación.")
                    return
                
                if logger:
                    logger.log(f"[MARKET M1] Operación {direction.upper()} abierta exitosamente (Ticket: {result.order})")
                    # Iniciar monitoreo en hilo separado
                    import threading
                    monitor_thread = threading.Thread(
                        target=CustomStrategies.manage_market_m1_position,
                        args=(simulation_instance, result.order, volume, direction, sl_pips, tp_pips, logger)
                    )
                    monitor_thread.daemon = True
                    monitor_thread.start()
            
            else:
                if logger: logger.error("[MARKET M1] No se pudieron calcular SL/TP.")
                
        except Exception as e:
            if logger:
                logger.error(f"[MARKET M1] Error en ejecución: {e}")




