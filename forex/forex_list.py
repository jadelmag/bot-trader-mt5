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
    def strategy_candle_pattern_reversal(df, lookback=200):
        """
        Estrategia FOREX optimizada de reversión con patrones de velas en niveles clave.
        Versión mejorada para EURUSD con parámetros específicos y gestión de riesgo avanzada.
        
        Args:
            df (DataFrame): DataFrame con datos OHLC y indicadores
            lookback (int): Periodo de lookback para niveles (200 velas)
        
        Returns:
            str: 'long', 'short' o None
        """
        
        # Configuración específica para EURUSD
        pair = "EURUSD"
        pair_settings = {
            "tolerance_base": 0.0015,  # 0.15%
            "rsi_overbought": 68,
            "rsi_oversold": 32,
            "min_atr_multiplier": 1.2,
            "volatility_threshold": 0.0008
        }
        
        # 1. VERIFICACIONES INICIALES
        if len(df) < lookback + 20:
            return None
            
        # Columnas requeridas
        required_columns = ['open', 'high', 'low', 'close', 'rsi', 'atr']
        if not all(col in df.columns for col in required_columns):
            return None
        
        # 2. FILTRO DE HORARIO (Sesiones de alta liquidez)
        current_time = df.index[-1] if hasattr(df.index[-1], 'hour') else pd.to_datetime(df.index[-1])
        current_hour = current_time.hour
        
        # Horarios de sesiones Londres/NY (GMT)
        london_session = range(7, 16)    # 7:00 - 16:00 GMT
        ny_session = range(12, 21)       # 12:00 - 21:00 GMT
        high_liquidity_hours = list(set(london_session) | set(ny_session))
        
        if current_hour not in high_liquidity_hours:
            return None
        
        # 3. DETECCIÓN MEJORADA DE SOPORTES/RESISTENCIAS
        recent_data = df.iloc[-lookback:]
        current_price = df['close'].iloc[-1]
        
        # Método 1: Pivot Points Diarios
        daily_high = recent_data['high'].max()
        daily_low = recent_data['low'].min()
        daily_close = recent_data['close'].iloc[-1]
        
        pivot = (daily_high + daily_low + daily_close) / 3
        r1 = 2 * pivot - daily_low
        s1 = 2 * pivot - daily_high
        r2 = pivot + (daily_high - daily_low)
        s2 = pivot - (daily_high - daily_low)
        
        # Método 2: Mínimos y máximos locales con ventana adaptativa
        window_size = max(10, lookback // 20)
        supports = []
        resistances = []
        
        for i in range(window_size, len(recent_data) - window_size, window_size // 2):
            window = recent_data.iloc[i-window_size:i+window_size]
            
            # Encontrar mínimos locales
            if window['low'].iloc[window_size] == window['low'].min():
                supports.append(window['low'].iloc[window_size])
            
            # Encontrar máximos locales  
            if window['high'].iloc[window_size] == window['high'].max():
                resistances.append(window['high'].iloc[window_size])
        
        # Método 3: Niveles psicológicos (redondeo)
        psychological_levels = []
        base_level = round(current_price, 3)
        for i in range(-5, 6):
            level = base_level + (i * 0.005)  # Cada 50 pips
            psychological_levels.append(level)
        
        # Combinar todos los niveles
        all_supports = supports + [s1, s2] + [l for l in psychological_levels if l < current_price]
        all_resistances = resistances + [r1, r2] + [l for l in psychological_levels if l > current_price]
        
        # Encontrar niveles más relevantes (más toques)
        support = max(all_supports, key=lambda x: sum(abs(recent_data['low'] - x) < 0.0005)) if all_supports else daily_low
        resistance = min(all_resistances, key=lambda x: sum(abs(recent_data['high'] - x) < 0.0005)) if all_resistances else daily_high
        
        # 4. TOLERANCIA ADAPTATIVA MEJORADA
        atr = df['atr'].iloc[-1]
        volatility_ratio = atr / current_price
        
        # Ajustar tolerancia basada en volatilidad
        if volatility_ratio > pair_settings["volatility_threshold"]:
            # Alta volatilidad - tolerancia más amplia
            tolerance = min(pair_settings["tolerance_base"] * 1.5, atr * pair_settings["min_atr_multiplier"])
        else:
            # Baja volatilidad - tolerancia más ajustada
            tolerance = max(pair_settings["tolerance_base"], atr * pair_settings["min_atr_multiplier"] * 0.8)
        
        tolerance = min(tolerance, pair_settings["tolerance_base"] * 2)
        
        # 5. DETECCIÓN DE PATRONES DE VELAS
        candle_data = df.to_dict('records')
        current_index = len(candle_data) - 1
        
        try:
            signals = CandlePatterns.detect_all_patterns(candle_data, current_index)
        except:
            # Fallback básico si hay error en la detección
            signals = {'long': [], 'short': [], 'neutral': []}
        
        # 6. INDICADORES DE CONFIRMACIÓN MEJORADOS
        rsi = df['rsi'].iloc[-1]
        rsi_prev = df['rsi'].iloc[-2] if len(df) > 1 else rsi
        
        # Volumen relativo (si disponible)
        volume_increase = False
        if 'tick_volume' in df.columns and len(df) > 20:
            avg_volume = df['tick_volume'].iloc[-50:].mean()
            current_volume = df['tick_volume'].iloc[-1]
            volume_increase = current_volume > avg_volume * 1.3
        
        # Momentum adicional
        price_above_ema = False
        if 'ema_20' in df.columns:
            price_above_ema = df['close'].iloc[-1] > df['ema_20'].iloc[-1]
        
        # 7. EVALUACIÓN LONG MEJORADA
        distance_to_support = abs(df['low'].iloc[-1] - support) / support
        is_near_support = distance_to_support < tolerance
        
        # Patrones alcistas con pesos
        bullish_weights = {
            'hammer': 2, 'inverted_hammer': 2, 'bullish_engulfing': 3,
            'piercing_line': 2, 'morning_star': 3, 'three_white_soldiers': 3
        }
        
        has_bullish_pattern = any(pattern in signals['long'] for pattern in bullish_weights.keys())
        bullish_pattern_strength = sum(bullish_weights.get(pattern, 1) for pattern in signals['long'] if pattern in bullish_weights)
        
        # Condiciones adicionales
        has_doji_at_support = 'doji' in signals['neutral'] and is_near_support
        rsi_oversold = rsi < pair_settings["rsi_oversold"] and rsi > rsi_prev
        price_confirmation = df['close'].iloc[-1] > df['open'].iloc[-1]
        strong_bullish_candle = (df['close'].iloc[-1] - df['open'].iloc[-1]) > (atr * 0.3)
        
        # SCORE LONG
        long_score = 0
        if is_near_support: long_score += 3
        if has_bullish_pattern: long_score += bullish_pattern_strength
        if has_doji_at_support: long_score += 1
        if rsi_oversold: long_score += 2
        if volume_increase: long_score += 1
        if price_confirmation: long_score += 1
        if strong_bullish_candle: long_score += 2
        if price_above_ema: long_score += 1
        
        # 8. EVALUACIÓN SHORT MEJORADA
        distance_to_resistance = abs(df['high'].iloc[-1] - resistance) / resistance
        is_near_resistance = distance_to_resistance < tolerance
        
        # Patrones bajistas con pesos
        bearish_weights = {
            'shooting_star': 2, 'hanging_man': 2, 'bearish_engulfing': 3,
            'dark_cloud_cover': 2, 'evening_star': 3, 'three_black_crows': 3
        }
        
        has_bearish_pattern = any(pattern in signals['short'] for pattern in bearish_weights.keys())
        bearish_pattern_strength = sum(bearish_weights.get(pattern, 1) for pattern in signals['short'] if pattern in bearish_weights)
        
        # Condiciones adicionales
        has_doji_at_resistance = 'doji' in signals['neutral'] and is_near_resistance
        rsi_overbought = rsi > pair_settings["rsi_overbought"] and rsi < rsi_prev
        price_confirmation_short = df['close'].iloc[-1] < df['open'].iloc[-1]
        strong_bearish_candle = (df['open'].iloc[-1] - df['close'].iloc[-1]) > (atr * 0.3)
        
        # SCORE SHORT
        short_score = 0
        if is_near_resistance: short_score += 3
        if has_bearish_pattern: short_score += bearish_pattern_strength
        if has_doji_at_resistance: short_score += 1
        if rsi_overbought: short_score += 2
        if volume_increase: short_score += 1
        if price_confirmation_short: short_score += 1
        if strong_bearish_candle: short_score += 2
        if not price_above_ema: short_score += 1
        
        # 9. DECISIÓN FINAL CON FILTROS ADICIONALES
        required_score = 6  # Score mínimo requerido
        
        # Evitar señales contradictorias
        if long_score >= required_score and short_score < required_score - 2:
            # Confirmación final: precio debe estar mostrando fuerza alcista
            if df['close'].iloc[-1] > df['close'].iloc[-2]:
                return 'long'
        
        if short_score >= required_score and long_score < required_score - 2:
            # Confirmación final: precio debe estar mostrando debilidad bajista
            if df['close'].iloc[-1] < df['close'].iloc[-2]:
                return 'short'
        
        return None

    @staticmethod
    def strategy_scalping_stochrsi_ema(df):
        """
        Estrategia de Scalping con doble filtro de tendencia (EMA) y confirmación de momentum (StochRSI).
        """
        required = ['close', 'stochrsi_k', 'stochrsi_d', 'ema_20', 'ema_50']
        if not all(col in df.columns for col in required):
            return None

        # Obtener valores actuales
        close = df['close'].iloc[-1]
        stoch_k = df['stochrsi_k'].iloc[-1]
        stoch_d = df['stochrsi_d'].iloc[-1]
        ema_20 = df['ema_20'].iloc[-1]
        ema_50 = df['ema_50'].iloc[-1]

        # Condiciones para LONG
        if (close > ema_20 > ema_50 and  # Tendencia alcista
            stoch_k > stoch_d and  # Cruce alcista en StochRSI
            stoch_k < 80):  # No sobrecomprado
            return 'long'

        # Condiciones para SHORT
        if (close < ema_20 < ema_50 and  # Tendencia bajista
            stoch_k < stoch_d and  # Cruce bajista en StochRSI
            stoch_k > 20):  # No sobrevendido
            return 'short'

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