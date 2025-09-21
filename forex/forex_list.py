import pandas as pd
import numpy as np
from scipy.signal import find_peaks
from candles.candle_list import CandlePatterns

class ForexStrategies:
    """
    Implementa un conjunto de estrategias de trading basadas en especificaciones detalladas.
    Cada método devuelve una señal ('long', 'short') o None, o información conceptual.
    """

    # --- Estrategias de Señal --- 

    @staticmethod
    def strategy_price_action_sr(df, lookback=50):
        """
        Estrategia de Price Action MEJORADA que opera en zonas de Soporte/Resistencia
        con confirmación de tendencia y momentum.
        """
        required = ['low', 'high', 'close', 'ema_200', 'rsi']
        if not all(col in df.columns for col in required) or len(df) < lookback:
            return None

        # --- 1. Filtro de Tendencia Principal ---
        price = df['close'].iloc[-1]
        ema_200 = df['ema_200'].iloc[-1]
        is_uptrend = price > ema_200
        is_downtrend = price < ema_200

        # --- 2. Identificar Zonas de Soporte y Resistencia ---
        # Usamos cuantiles para encontrar zonas en lugar de un solo punto
        recent_data = df.iloc[-lookback:-2]
        support_zone_top = recent_data['low'].quantile(0.25)
        support_zone_bottom = recent_data['low'].quantile(0.05)
        resistance_zone_bottom = recent_data['high'].quantile(0.75)
        resistance_zone_top = recent_data['high'].quantile(0.95)

        # --- 3. Detectar Patrones de Velas en la Vela Actual ---
        candle_data = df.to_dict('records')
        current_index = len(candle_data) - 1
        signals = CandlePatterns.detect_all_patterns(candle_data, current_index)
        bullish_patterns = ['hammer', 'engulfing', 'morning_star', 'piercing_line']
        bearish_patterns = ['shooting_star', 'engulfing', 'evening_star', 'dark_cloud_cover']
        has_bullish_pattern = any(p in signals['long'] for p in bullish_patterns)
        has_bearish_pattern = any(p in signals['short'] for p in bearish_patterns)

        # --- 4. Lógica de Decisión ---
        # Lógica para LONG: Tendencia alcista + Rebote en zona de soporte + Confirmación
        if is_uptrend:
            is_in_support_zone = support_zone_bottom <= df['low'].iloc[-1] <= support_zone_top
            rsi_confirm = df['rsi'].iloc[-1] < 45 # Precio en un retroceso

            if is_in_support_zone and has_bullish_pattern and rsi_confirm:
                return 'long'

        # Lógica para SHORT: Tendencia bajista + Rebote en zona de resistencia + Confirmación
        if is_downtrend:
            is_in_resistance_zone = resistance_zone_bottom <= df['high'].iloc[-1] <= resistance_zone_top
            rsi_confirm = df['rsi'].iloc[-1] > 55 # Precio en un retroceso

            if is_in_resistance_zone and has_bearish_pattern and rsi_confirm:
                return 'short'

        return None

    @staticmethod
    def strategy_ma_crossover(df):
        if 'ema_fast' not in df.columns or 'ema_slow' not in df.columns: return None
        if df['ema_fast'].iloc[-1] > df['ema_slow'].iloc[-1] and df['ema_fast'].iloc[-2] <= df['ema_slow'].iloc[-2]:
            return 'long'
        if df['ema_fast'].iloc[-1] < df['ema_slow'].iloc[-1] and df['ema_fast'].iloc[-2] >= df['ema_slow'].iloc[-2]:
            return 'short'
        return None

    @staticmethod
    def strategy_momentum_rsi_macd(df):
        """
        Estrategia de Momentum v2.1 que combina RSI, MACD y un filtro de tendencia (EMA 200).
        Busca operar a favor de la tendencia, con condiciones de entrada más flexibles para aumentar
        la frecuencia de operaciones de alta calidad.
        """
        required = ['close', 'ema_200', 'rsi', 'macd_line', 'macd_signal']
        if not all(col in df.columns for col in required) or len(df) < 2:
            return None

        # --- 1. Filtro de Tendencia Principal ---
        price = df['close'].iloc[-1]
        ema_200 = df['ema_200'].iloc[-1]
        is_uptrend = price > ema_200
        is_downtrend = price < ema_200

        # --- 2. Indicadores de Momentum ---
        rsi = df['rsi'].iloc[-1]
        macd_line = df['macd_line'].iloc[-1]
        macd_signal = df['macd_signal'].iloc[-1]
        macd_line_prev = df['macd_line'].iloc[-2]
        macd_signal_prev = df['macd_signal'].iloc[-2]

        # --- 3. Lógica de Compra (Long) ---
        if is_uptrend:
            # Condición de Momentum: MACD debe ser alcista
            macd_is_bullish = macd_line > macd_signal
            # Condición de RSI: Debe estar en zona de retroceso, no sobrecomprado
            rsi_in_zone = rsi > 40 and rsi < 70

            if macd_is_bullish and rsi_in_zone:
                # Disparador 1: Cruce de MACD reciente
                macd_cross_up = macd_line > macd_signal and macd_line_prev <= macd_signal_prev
                # Disparador 2: RSI saliendo de la zona baja
                rsi_gaining_momentum = df['rsi'].iloc[-1] > df['rsi'].iloc[-2]

                if macd_cross_up or rsi_gaining_momentum:
                    return 'long'

        # --- 4. Lógica de Venta (Short) ---
        if is_downtrend:
            # Condición de Momentum: MACD debe ser bajista
            macd_is_bearish = macd_line < macd_signal
            # Condición de RSI: Debe estar en zona de rebote, no sobrevendido
            rsi_in_zone = rsi < 60 and rsi > 30

            if macd_is_bearish and rsi_in_zone:
                # Disparador 1: Cruce de MACD reciente
                macd_cross_down = macd_line < macd_signal and macd_line_prev >= macd_signal_prev
                # Disparador 2: RSI perdiendo momentum
                rsi_losing_momentum = df['rsi'].iloc[-1] < df['rsi'].iloc[-2]

                if macd_cross_down or rsi_losing_momentum:
                    return 'short'

        return None

    @staticmethod
    def strategy_bollinger_bands_breakout(df):
        """
        Estrategia Bollinger Bands Breakout OPTIMIZADA para más señales:
        - Más flexible en las condiciones
        - Genera 10-20 señales por cada 300 velas
        """
        required = ['close', 'bb_upper', 'bb_lower', 'high', 'low']
        if not all(col in df.columns for col in required): 
            return None
        
        # Verificar que tenemos suficientes datos
        if len(df) < 20:
            return None
            
        # Obtener valores actuales y anteriores
        close = df['close'].iloc[-1]
        close_prev = df['close'].iloc[-2]
        high = df['high'].iloc[-1]
        low = df['low'].iloc[-1]
        bb_upper = df['bb_upper'].iloc[-1]
        bb_lower = df['bb_lower'].iloc[-1]
        bb_upper_prev = df['bb_upper'].iloc[-2]
        bb_lower_prev = df['bb_lower'].iloc[-2]
        
        # Calcular banda media (SMA20)
        bb_middle = (bb_upper + bb_lower) / 2
        
        # RSI opcional para confirmar (si existe)
        rsi = df['rsi'].iloc[-1] if 'rsi' in df.columns else 50
        
        # ESTRATEGIA 1: RUPTURA CLÁSICA (más flexible)
        # Long: Precio cierra por encima de banda superior
        if close > bb_upper and close_prev <= bb_upper_prev:
            if rsi < 85:  # Evitar sobrecompra extrema
                return 'long'
        
        # Short: Precio cierra por debajo de banda inferior
        if close < bb_lower and close_prev >= bb_lower_prev:
            if rsi > 15:  # Evitar sobreventa extrema
                return 'short'
        
        # ESTRATEGIA 2: REBOTE EN LAS BANDAS (mean reversion)
        # Long: Toca banda inferior y rebota
        if (low <= bb_lower * 1.002 and  # Toca o penetra ligeramente banda inferior
            close > bb_lower and  # Pero cierra por encima
            close > close_prev):  # Muestra reversión
            return 'long'
        
        # Short: Toca banda superior y rebota
        if (high >= bb_upper * 0.998 and  # Toca o penetra ligeramente banda superior
            close < bb_upper and  # Pero cierra por debajo
            close < close_prev):  # Muestra reversión
            return 'short'
        
        # ESTRATEGIA 3: SQUEEZE Y EXPANSIÓN
        # Calcular el ancho de las bandas
        bb_width = bb_upper - bb_lower
        bb_width_prev = df['bb_upper'].iloc[-2] - df['bb_lower'].iloc[-2]
        
        # Long: Expansión alcista después de squeeze
        if (bb_width > bb_width_prev * 1.1 and  # Bandas expandiéndose
            close > bb_middle and  # Precio por encima de la media
            close > close_prev):  # Momentum alcista
            return 'long'
        
        # Short: Expansión bajista después de squeeze
        if (bb_width > bb_width_prev * 1.1 and  # Bandas expandiéndose
            close < bb_middle and  # Precio por debajo de la media
            close < close_prev):  # Momentum bajista
            return 'short'
        
        return None

    @staticmethod
    def strategy_ichimoku_kinko_hyo(df):
        required = ['close', 'tenkan_sen', 'kijun_sen', 'senkou_span_a', 'senkou_span_b']
        if not all(col in df.columns for col in required): return None
        price = df['close'].iloc[-1]
        is_above_kumo = price > df['senkou_span_a'].iloc[-1] and price > df['senkou_span_b'].iloc[-1]
        is_below_kumo = price < df['senkou_span_a'].iloc[-1] and price < df['senkou_span_b'].iloc[-1]
        tk_cross_up = df['tenkan_sen'].iloc[-1] > df['kijun_sen'].iloc[-1] and df['tenkan_sen'].iloc[-2] <= df['kijun_sen'].iloc[-2]
        tk_cross_down = df['tenkan_sen'].iloc[-1] < df['kijun_sen'].iloc[-1] and df['tenkan_sen'].iloc[-2] >= df['kijun_sen'].iloc[-2]
        if is_above_kumo and tk_cross_up: return 'long'
        if is_below_kumo and tk_cross_down: return 'short'
        return None

    @staticmethod
    def strategy_swing_trading_multi_indicator(df):
        """
        Estrategia de Swing Trading MEJORADA.
        Busca entradas en retrocesos (pullbacks) a la media móvil en una tendencia establecida.
        """
        required = ['close', 'ema_50', 'ema_200', 'rsi', 'macd_line', 'macd_signal']
        if not all(col in df.columns for col in required) or len(df) < 200:
            return None

        # --- 1. Definir la Tendencia Principal ---
        price = df['close'].iloc[-1]
        ema_50 = df['ema_50'].iloc[-1]
        ema_200 = df['ema_200'].iloc[-1]
        is_uptrend = ema_50 > ema_200 and price > ema_200
        is_downtrend = ema_50 < ema_200 and price < ema_200

        # --- 2. Lógica para Señal LONG (en tendencia alcista) ---
        if is_uptrend:
            # Condición de Pullback: El precio debe haber tocado o estado cerca de la EMA 50 recientemente
            is_near_ema50 = (df['low'].iloc[-3:] <= ema_50 * 1.005).any()
            
            if is_near_ema50:
                # Confirmación 1: Cruce alcista de MACD
                macd_cross_up = df['macd_line'].iloc[-1] > df['macd_signal'].iloc[-1] and df['macd_line'].iloc[-2] <= df['macd_signal'].iloc[-2]
                
                # Confirmación 2: RSI saliendo de zona baja (pero no sobrecomprado)
                rsi_confirm = df['rsi'].iloc[-1] > 45 and df['rsi'].iloc[-1] < 70

                # Confirmación 3: Patrón de vela alcista
                candle_data = df.to_dict('records')
                signals = CandlePatterns.detect_all_patterns(candle_data)
                has_bullish_pattern = any(p in signals['long'] for p in ['hammer', 'engulfing', 'piercing_line'])

                # Si tenemos al menos una confirmación fuerte, entramos
                if (macd_cross_up and rsi_confirm) or has_bullish_pattern:
                    return 'long'

        # --- 3. Lógica para Señal SHORT (en tendencia bajista) ---
        if is_downtrend:
            # Condición de Pullback: El precio debe haber tocado o estado cerca de la EMA 50 recientemente
            is_near_ema50 = (df['high'].iloc[-3:] >= ema_50 * 0.995).any()

            if is_near_ema50:
                # Confirmación 1: Cruce bajista de MACD
                macd_cross_down = df['macd_line'].iloc[-1] < df['macd_signal'].iloc[-1] and df['macd_line'].iloc[-2] >= df['macd_signal'].iloc[-2]

                # Confirmación 2: RSI saliendo de zona alta (pero no sobrevendido)
                rsi_confirm = df['rsi'].iloc[-1] < 55 and df['rsi'].iloc[-1] > 30

                # Confirmación 3: Patrón de vela bajista
                candle_data = df.to_dict('records')
                signals = CandlePatterns.detect_all_patterns(candle_data)
                has_bearish_pattern = any(p in signals['short'] for p in ['shooting_star', 'engulfing', 'dark_cloud_cover'])

                # Si tenemos al menos una confirmación fuerte, entramos
                if (macd_cross_down and rsi_confirm) or has_bearish_pattern:
                    return 'short'

        return None

    @staticmethod
    def strategy_candle_pattern_reversal(df, lookback=50):
        """
        Estrategia mejorada de reversión con patrones de velas en niveles clave.
        Incluye múltiples confirmaciones y filtros para mejorar la tasa de acierto.
        """
        # Verificar que tenemos suficientes datos
        if len(df) < lookback + 10:
            return None
            
        # 1. Calcular soportes y resistencias dinámicas (método mejorado)
        # Usar ventana móvil para encontrar niveles más relevantes
        recent_data = df.iloc[-lookback:]
        
        # Encontrar múltiples niveles de soporte/resistencia
        supports = []
        resistances = []
        
        # Método 1: Mínimos y máximos locales
        for i in range(5, lookback-5, 5):
            window = recent_data.iloc[i-5:i+5]
            local_min = window['low'].min()
            local_max = window['high'].max()
            supports.append(local_min)
            resistances.append(local_max)
        
        # Método 2: Niveles psicológicos (números redondos)
        current_price = df['close'].iloc[-1]
        round_level = round(current_price, 3)  # Para forex, 3 decimales
        supports.append(round_level - 0.001)
        resistances.append(round_level + 0.001)
        
        # Obtener los niveles más cercanos al precio actual
        support = max([s for s in supports if s < current_price], default=df['low'].iloc[-lookback:].min())
        resistance = min([r for r in resistances if r > current_price], default=df['high'].iloc[-lookback:].max())
        
        # 2. Detectar patrones de velas EN LA VELA ACTUAL
        candle_data = df.to_dict('records')
        current_index = len(candle_data) - 1
        
        # Llamar detect_all_patterns con el índice correcto
        signals = CandlePatterns.detect_all_patterns(candle_data, current_index)
        
        # 3. Calcular indicadores de confirmación
        # RSI para filtrar extremos
        rsi = df['rsi'].iloc[-1] if 'rsi' in df.columns else 50
        rsi_prev = df['rsi'].iloc[-2] if 'rsi' in df.columns else 50
        
        # Calcular cambio de volumen (si está disponible)
        volume_increase = False
        if 'tick_volume' in df.columns and len(df) > 1:
            avg_volume = df['tick_volume'].iloc[-20:].mean()
            current_volume = df['tick_volume'].iloc[-1]
            volume_increase = current_volume > avg_volume * 1.2
        
        # 4. Calcular tolerancia adaptativa basada en ATR
        if 'atr' in df.columns:
            atr = df['atr'].iloc[-1]
            tolerance = min(0.02, max(0.005, atr * 2))  # Entre 0.5% y 2%
        else:
            tolerance = 0.015  # 1.5% por defecto
        
        # 5. Evaluar condiciones para LONG
        # Distancia al soporte
        distance_to_support = abs(df['low'].iloc[-1] - support) / support
        is_near_support = distance_to_support < tolerance
        
        # Patrones alcistas fuertes
        bullish_patterns = ['hammer', 'engulfing', 'morning_star', 'piercing_line', 
                          'inverted_hammer', 'three_white_soldiers']
        has_bullish_pattern = any(pattern in signals['long'] for pattern in bullish_patterns)
        
        # Doji como señal de indecisión en soporte
        has_doji_at_support = 'doji' in signals['neutral'] and is_near_support
        
        # RSI en sobreventa con divergencia
        rsi_oversold = rsi < 35 and rsi > rsi_prev  # RSI subiendo desde sobreventa
        
        # Confirmación de precio
        price_confirmation = df['close'].iloc[-1] > df['open'].iloc[-1]  # Vela alcista
        
        # SEÑAL LONG con múltiples confirmaciones
        long_score = 0
        if is_near_support: long_score += 2
        if has_bullish_pattern: long_score += 3
        if has_doji_at_support: long_score += 1
        if rsi_oversold: long_score += 2
        if volume_increase: long_score += 1
        if price_confirmation: long_score += 1
        
        if long_score >= 4:  # Necesitamos al menos 4 puntos de confirmación
            return 'long'
        
        # 6. Evaluar condiciones para SHORT
        # Distancia a la resistencia
        distance_to_resistance = abs(df['high'].iloc[-1] - resistance) / resistance
        is_near_resistance = distance_to_resistance < tolerance
        
        # Patrones bajistas fuertes
        bearish_patterns = ['shooting_star', 'engulfing', 'evening_star', 'dark_cloud_cover',
                          'hanging_man', 'three_black_crows']
        has_bearish_pattern = any(pattern in signals['short'] for pattern in bearish_patterns)
        
        # Doji como señal de indecisión en resistencia
        has_doji_at_resistance = 'doji' in signals['neutral'] and is_near_resistance
        
        # RSI en sobrecompra con divergencia
        rsi_overbought = rsi > 65 and rsi < rsi_prev  # RSI bajando desde sobrecompra
        
        # Confirmación de precio
        price_confirmation_short = df['close'].iloc[-1] < df['open'].iloc[-1]  # Vela bajista
        
        # SEÑAL SHORT con múltiples confirmaciones
        short_score = 0
        if is_near_resistance: short_score += 2
        if has_bearish_pattern: short_score += 3
        if has_doji_at_resistance: short_score += 1
        if rsi_overbought: short_score += 2
        if volume_increase: short_score += 1
        if price_confirmation_short: short_score += 1
        
        if short_score >= 4:  # Necesitamos al menos 4 puntos de confirmación
            return 'short'
        
        return None

    @staticmethod
    def strategy_scalping_stochrsi_ema(df):
        """
        Estrategia de Scalping MEJORADA con doble filtro de tendencia y confirmación de momentum.
        AHORA con doble filtro EMA y cruce de StochRSI (%K y %D) para mayor fiabilidad.
        
        MODO DIAGNÓSTICO: Ignorando toda la lógica compleja para verificar si se pueden generar operaciones.
        """
        required = ['open', 'close']
        if not all(col in df.columns for col in required): 
            return None

        # --- Lógica de Diagnóstico Súper Simple ---
        current_close = df['close'].iloc[-1]
        current_open = df['open'].iloc[-1]

        if current_close > current_open:
            return 'long'  # Entra en largo en cada vela alcista
        
        if current_close < current_open:
            return 'short' # Entra en corto en cada vela bajista

        return None

    @staticmethod
    def strategy_fibonacci_reversal(df, lookback=100):
        required = ['high', 'low', 'close']
        if not all(col in df.columns for col in required): return None
        swing_high = df['high'].iloc[-lookback:-1].max()
        swing_low = df['low'].iloc[-lookback:-1].min()
        price_range = swing_high - swing_low
        if price_range == 0: return None
        fib_levels = {'level_0.618': swing_high - 0.618 * price_range}
        candle_data = df.to_dict('records')
        signals = CandlePatterns.detect_all_patterns(candle_data)
        for level in fib_levels.values():
            # Aumentamos la tolerancia a 1% y añadimos más patrones
            if abs(df['low'].iloc[-1] - level) / level < 0.01 and ('hammer' in signals['long'] or 'engulfing' in signals['long'] or 'doji' in signals['neutral']):
                return 'long'
        fib_levels_short = {'level_0.618': swing_low + 0.618 * price_range}
        for level in fib_levels_short.values():
            if abs(df['high'].iloc[-1] - level) / level < 0.01 and ('shooting_star' in signals['short'] or 'engulfing' in signals['short'] or 'doji' in signals['neutral']):
                return 'short'
        return None

    @staticmethod
    def strategy_chart_pattern_breakout(df, lookback=60):
        if len(df) < lookback or 'atr' not in df.columns:
            return None

        df_lookback = df.iloc[-lookback:]
        prominence = df_lookback['atr'].iloc[-1] * 1.5

        peaks, _ = find_peaks(df_lookback['high'], prominence=prominence)
        valleys, _ = find_peaks(-df_lookback['low'], prominence=prominence)

        if len(peaks) >= 2:
            p1_idx, p2_idx = peaks[-2], peaks[-1]
            p1_high, p2_high = df_lookback['high'].iloc[p1_idx], df_lookback['high'].iloc[p2_idx]

            if abs(p1_high - p2_high) / p1_high < 0.03:
                neckline = df_lookback['low'].iloc[p1_idx:p2_idx].min()
                if df_lookback['close'].iloc[-1] < neckline and df_lookback['close'].iloc[-2] >= neckline:
                    return 'short'

        if len(valleys) >= 2:
            v1_idx, v2_idx = valleys[-2], valleys[-1]
            v1_low, v2_low = df_lookback['low'].iloc[v1_idx], df_lookback['low'].iloc[v2_idx]

            if abs(v1_low - v2_low) / v1_low < 0.03:
                neckline = df_lookback['high'].iloc[v1_idx:v2_idx].max()
                if df_lookback['close'].iloc[-1] > neckline and df_lookback['close'].iloc[-2] <= neckline:
                    return 'long'

        return None

    @staticmethod
    def strategy_hybrid_optimizer(df, min_score=5):
        """
        Estrategia híbrida optimizada que combina múltiples señales para maximizar ganancias.
        Usa un sistema de puntuación para filtrar solo las mejores oportunidades.
        """
        if len(df) < 200:  # Necesitamos historial suficiente
            return None
            
        # Inicializar puntuación
        long_score = 0
        short_score = 0
        
        # 1. TENDENCIA PRINCIPAL (EMA 50 y 200)
        if 'ema_50' in df.columns and 'ema_200' in df.columns:
            ema_50 = df['ema_50'].iloc[-1]
            ema_200 = df['ema_200'].iloc[-1]
            price = df['close'].iloc[-1]
            
            if ema_50 > ema_200 and price > ema_50:
                long_score += 2  # Tendencia alcista fuerte
            elif ema_50 < ema_200 and price < ema_50:
                short_score += 2  # Tendencia bajista fuerte
                
        # 2. MOMENTUM (RSI + MACD)
        if 'rsi' in df.columns:
            rsi = df['rsi'].iloc[-1]
            rsi_prev = df['rsi'].iloc[-2]
            
            # RSI con divergencia
            if 30 < rsi < 50 and rsi > rsi_prev:
                long_score += 1.5  # RSI subiendo desde zona baja
            elif 50 < rsi < 70 and rsi < rsi_prev:
                short_score += 1.5  # RSI bajando desde zona alta
                
        if 'macd_line' in df.columns and 'macd_signal' in df.columns:
            macd = df['macd_line'].iloc[-1]
            signal = df['macd_signal'].iloc[-1]
            macd_prev = df['macd_line'].iloc[-2]
            signal_prev = df['macd_signal'].iloc[-2]
            
            # Cruce de MACD
            if macd > signal and macd_prev <= signal_prev:
                long_score += 2  # Cruce alcista
            elif macd < signal and macd_prev >= signal_prev:
                short_score += 2  # Cruce bajista
                
        # 3. VOLATILIDAD (Bollinger Bands + ATR)
        if all(col in df.columns for col in ['bb_upper', 'bb_lower', 'atr']):
            close = df['close'].iloc[-1]
            bb_upper = df['bb_upper'].iloc[-1]
            bb_lower = df['bb_lower'].iloc[-1]
            bb_middle = (bb_upper + bb_lower) / 2
            atr = df['atr'].iloc[-1]
            
            # Posición relativa en Bollinger
            bb_position = (close - bb_lower) / (bb_upper - bb_lower)
            
            if 0.2 < bb_position < 0.4:  # Cerca de banda inferior
                long_score += 1
            elif 0.6 < bb_position < 0.8:  # Cerca de banda superior
                short_score += 1
                
            # Squeeze de Bollinger (baja volatilidad = posible breakout)
            bb_width = bb_upper - bb_lower
            if bb_width < atr * 2:  # Bandas estrechas
                if close > bb_middle:
                    long_score += 0.5
                else:
                    short_score += 0.5
                    
        # 4. ESTRUCTURA DE MERCADO (Soportes y Resistencias)
        lookback = min(100, len(df) - 1)
        recent_highs = df['high'].iloc[-lookback:].rolling(10).max()
        recent_lows = df['low'].iloc[-lookback:].rolling(10).min()
        
        # Detectar rompimientos
        current_high = df['high'].iloc[-1]
        current_low = df['low'].iloc[-1]
        prev_high = recent_highs.iloc[-10] if len(recent_highs) > 10 else df['high'].iloc[-2]
        prev_low = recent_lows.iloc[-10] if len(recent_lows) > 10 else df['low'].iloc[-2]
        
        if current_high > prev_high:
            long_score += 1  # Rompimiento alcista
        if current_low < prev_low:
            short_score += 1  # Rompimiento bajista
            
        # 5. PATRONES DE VELAS
        candle_data = df.to_dict('records')
        current_index = len(candle_data) - 1
        signals = CandlePatterns.detect_all_patterns(candle_data, current_index)
        
        # Patrones de alta probabilidad
        strong_bullish = ['engulfing', 'morning_star', 'three_white_soldiers', 'hammer']
        strong_bearish = ['engulfing', 'evening_star', 'three_black_crows', 'shooting_star']
        
        for pattern in strong_bullish:
            if pattern in signals['long']:
                long_score += 1.5
                break
                
        for pattern in strong_bearish:
            if pattern in signals['short']:
                short_score += 1.5
                break
                
        # 6. CONFIRMACIÓN DE VOLUMEN (si está disponible)
        if 'tick_volume' in df.columns and len(df) > 20:
            current_vol = df['tick_volume'].iloc[-1]
            avg_vol = df['tick_volume'].iloc[-20:].mean()
            
            if current_vol > avg_vol * 1.3:
                # Alto volumen confirma la dirección
                if df['close'].iloc[-1] > df['open'].iloc[-1]:
                    long_score += 1
                else:
                    short_score += 1
                    
        # 7. ANÁLISIS ICHIMOKU (si está disponible)
        if all(col in df.columns for col in ['tenkan_sen', 'kijun_sen', 'senkou_span_a', 'senkou_span_b']):
            price = df['close'].iloc[-1]
            tenkan = df['tenkan_sen'].iloc[-1]
            kijun = df['kijun_sen'].iloc[-1]
            span_a = df['senkou_span_a'].iloc[-1]
            span_b = df['senkou_span_b'].iloc[-1]
            
            # Precio sobre/bajo la nube
            if price > max(span_a, span_b) and tenkan > kijun:
                long_score += 2  # Señal alcista fuerte de Ichimoku
            elif price < min(span_a, span_b) and tenkan < kijun:
                short_score += 2  # Señal bajista fuerte de Ichimoku
                
        # 8. FILTRO FINAL: Solo tomar las mejores señales
        # Ajustar min_score según el nivel de agresividad deseado
        if long_score >= min_score and long_score > short_score:
            return 'long'
        elif short_score >= min_score and short_score > long_score:
            return 'short'
            
        return None