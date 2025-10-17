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
        Estrategia de Price Action con Soporte/Resistencia FLEXIBLE.
        
        Lógica:
        - Identifica zonas de soporte/resistencia usando cuantiles
        - LONG: Precio en zona inferior + RSI favorable + momentum alcista
        - SHORT: Precio en zona superior + RSI favorable + momentum bajista
        - Confirmación con análisis de velas pero sin ser excesivamente restrictivo
        """
        required = ['low', 'high', 'close', 'open', 'ema_200', 'rsi']
        if not all(col in df.columns for col in required) or len(df) < lookback:
            return None

        # --- 1. Obtener datos actuales ---
        price = df['close'].iloc[-1]
        price_prev = df['close'].iloc[-2]
        open_price = df['open'].iloc[-1]
        ema_200 = df['ema_200'].iloc[-1]
        rsi = df['rsi'].iloc[-1]
        rsi_prev = df['rsi'].iloc[-2]
        
        # Tendencia general (flexible, permite reversiones)
        is_uptrend_or_neutral = price > ema_200 * 0.99  # 1% tolerancia
        is_downtrend_or_neutral = price < ema_200 * 1.01  # 1% tolerancia

        # --- 2. Identificar Zonas de Soporte y Resistencia ---
        recent_data = df.iloc[-lookback:]
        
        # Zonas de soporte (cuartiles inferiores)
        support_zone_top = recent_data['low'].quantile(0.35)  # Zona más amplia: 35%
        support_zone_bottom = recent_data['low'].quantile(0.10)
        
        # Zonas de resistencia (cuartiles superiores)
        resistance_zone_bottom = recent_data['high'].quantile(0.65)  # Zona más amplia: 65%
        resistance_zone_top = recent_data['high'].quantile(0.90)

        # --- 3. Confirmación de Momentum ---
        is_bullish_candle = price > open_price
        is_bearish_candle = price < open_price
        
        price_momentum_up = price > price_prev
        price_momentum_down = price < price_prev
        
        rsi_gaining = rsi > rsi_prev
        rsi_losing = rsi < rsi_prev

        # --- 4. LÓGICA FLEXIBLE PARA LONG ---
        current_price_position = (price - support_zone_top) / (resistance_zone_bottom - support_zone_top) if (resistance_zone_bottom - support_zone_top) > 0 else 0.5
        
        # Confirmación de reversión (flexible: 2 velas en lugar de 3)
        if len(df) >= 2:
            price_2_ago = df['close'].iloc[-2]
            bullish_reversal = (price_2_ago < price_prev < price) or (price > price_prev and is_bullish_candle)
            bearish_reversal = (price_2_ago > price_prev > price) or (price < price_prev and is_bearish_candle)
        else:
            bullish_reversal = price_momentum_up and is_bullish_candle
            bearish_reversal = price_momentum_down and is_bearish_candle
        
        # LONG: En zona inferior (más amplia) + confirmaciones
        is_in_lower_zone = current_price_position <= 0.4  # 40% inferior (antes 30%)
        if (is_uptrend_or_neutral and is_in_lower_zone and 
            rsi < 55 and rsi_gaining and bullish_reversal):  # RSI más flexible
            return 'long'
        
        # SHORT: En zona superior (más amplia) + confirmaciones
        is_in_upper_zone = current_price_position >= 0.6  # 40% superior (antes 30%)
        if (is_downtrend_or_neutral and is_in_upper_zone and 
            rsi > 45 and rsi_losing and bearish_reversal):  # RSI más flexible
            return 'short'

        return None

    @staticmethod
    def strategy_momentum_rsi_macd(df):
        """
        Estrategia de Momentum FLEXIBLE que combina RSI, MACD y tendencia.
        
        Lógica:
        - LONG: MACD alcista + RSI favorable + momentum positivo
        - SHORT: MACD bajista + RSI favorable + momentum negativo
        - Filtros flexibles para más señales de calidad
        """
        required = ['close', 'ema_200', 'rsi', 'macd_line', 'macd_signal']
        if not all(col in df.columns for col in required) or len(df) < 2:
            return None

        # --- 1. Filtro de Tendencia FLEXIBLE ---
        price = df['close'].iloc[-1]
        ema_200 = df['ema_200'].iloc[-1]
        
        # Permite operar cerca de EMA_200 (zona de reversión)
        is_uptrend_or_neutral = price > ema_200 * 0.99  # 1% tolerancia
        is_downtrend_or_neutral = price < ema_200 * 1.01

        # --- 2. Indicadores de Momentum ---
        rsi = df['rsi'].iloc[-1]
        rsi_prev = df['rsi'].iloc[-2]
        macd_line = df['macd_line'].iloc[-1]
        macd_signal = df['macd_signal'].iloc[-1]
        macd_line_prev = df['macd_line'].iloc[-2]
        macd_signal_prev = df['macd_signal'].iloc[-2]

        # --- 3. LÓGICA FLEXIBLE PARA LONG ---
        if is_uptrend_or_neutral:
            # MACD: Cruce alcista O posición alcista con momentum
            macd_cross_up = macd_line > macd_signal and macd_line_prev <= macd_signal_prev
            macd_bullish = macd_line > macd_signal and macd_line > macd_line_prev
            
            # RSI: Zona FLEXIBLE pero efectiva
            rsi_favorable = 30 <= rsi <= 60 and rsi > rsi_prev  # Zona amplia
            
            # Confirmación de precio
            price_confirmation = price > df['close'].iloc[-2]
            
            # Al menos 2 de 3 condiciones deben cumplirse
            conditions = [
                macd_cross_up or macd_bullish,
                rsi_favorable,
                price_confirmation
            ]
            
            if sum(conditions) >= 2:
                return 'long'

        # --- 4. LÓGICA FLEXIBLE PARA SHORT ---
        if is_downtrend_or_neutral:
            # MACD: Cruce bajista O posición bajista con momentum
            macd_cross_down = macd_line < macd_signal and macd_line_prev >= macd_signal_prev
            macd_bearish = macd_line < macd_signal and macd_line < macd_line_prev
            
            # RSI: Zona FLEXIBLE pero efectiva
            rsi_favorable = 40 <= rsi <= 70 and rsi < rsi_prev  # Zona amplia
            
            # Confirmación de precio
            price_confirmation = price < df['close'].iloc[-2]
            
            # Al menos 2 de 3 condiciones deben cumplirse
            conditions = [
                macd_cross_down or macd_bearish,
                rsi_favorable,
                price_confirmation
            ]
            
            if sum(conditions) >= 2:
                return 'short'

        return None

    @staticmethod
    def strategy_bollinger_bands_breakout(df):
        """
        Estrategia Bollinger Bands MEAN REVERSION FLEXIBLE (Rebote en Bandas).
        
        Lógica:
        - LONG: Precio cerca de banda inferior + señales de rebote
        - SHORT: Precio cerca de banda superior + señales de rechazo
        - Confirmación flexible con RSI y momentum
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
        
        # Calcular banda media (SMA20)
        bb_middle = (bb_upper + bb_lower) / 2
        
        # RSI para confirmar condiciones
        rsi = df['rsi'].iloc[-1] if 'rsi' in df.columns else 50
        rsi_prev = df['rsi'].iloc[-2] if 'rsi' in df.columns and len(df) > 1 else rsi
        
        # ESTRATEGIA FLEXIBLE: REBOTE EN LAS BANDAS
        
        # Verificar reversión con 2 velas (más flexible)
        if len(df) >= 2:
            close_2_ago = df['close'].iloc[-2]
            
            # Reversión alcista: precio bajando + rebote
            confirmed_bullish_reversal = (
                close_2_ago > close_prev and  # Vela anterior bajista
                close > close_prev  # Rebote confirmado
            )
            
            # Reversión bajista: precio subiendo + rechazo
            confirmed_bearish_reversal = (
                close_2_ago < close_prev and  # Vela anterior alcista
                close < close_prev  # Rechazo confirmado
            )
        else:
            confirmed_bullish_reversal = close > close_prev
            confirmed_bearish_reversal = close < close_prev
        
        # LONG: Cerca de banda inferior + reversión
        touching_lower = low <= bb_lower * 1.005  # 0.5% tolerancia
        closing_above_lower = close > bb_lower
        rsi_oversold_flexible = rsi < 45 and rsi > rsi_prev  # Más flexible
        
        if (touching_lower and closing_above_lower and 
            confirmed_bullish_reversal and rsi_oversold_flexible):
            return 'long'
        
        # SHORT: Cerca de banda superior + reversión
        touching_upper = high >= bb_upper * 0.995  # 0.5% tolerancia
        closing_below_upper = close < bb_upper
        rsi_overbought_flexible = rsi > 55 and rsi < rsi_prev  # Más flexible
        
        if (touching_upper and closing_below_upper and 
            confirmed_bearish_reversal and rsi_overbought_flexible):
            return 'short'
        
        return None

    @staticmethod
    def strategy_swing_trading_multi_indicator(df):
        """
        Estrategia de Swing Trading FLEXIBLE con múltiples indicadores.
        Busca entradas en retrocesos con confirmaciones inteligentes.
        """
        required = ['close', 'ema_50', 'ema_200', 'rsi', 'macd_line', 'macd_signal']
        if not all(col in df.columns for col in required) or len(df) < 200:
            return None

        # --- 1. Definir Tendencia Principal (FLEXIBLE) ---
        price = df['close'].iloc[-1]
        ema_50 = df['ema_50'].iloc[-1]
        ema_200 = df['ema_200'].iloc[-1]
        
        # Tendencia con tolerancia razonable
        is_strong_uptrend = ema_50 > ema_200 * 1.001 and price > ema_50 * 0.995
        is_strong_downtrend = ema_50 < ema_200 * 0.999 and price < ema_50 * 1.005

        # --- 2. Lógica LONG (Pullback en tendencia alcista) ---
        if is_strong_uptrend:
            # Pullback: precio cerca o tocó EMA_50 en últimas 5 velas
            pullback_detected = (df['low'].iloc[-5:] <= ema_50 * 1.005).any()
            
            if pullback_detected:
                # CONFIRMACIÓN 1: MACD cruzando al alza O alcista con momentum
                macd_cross_up = (df['macd_line'].iloc[-1] > df['macd_signal'].iloc[-1] and 
                            df['macd_line'].iloc[-2] <= df['macd_signal'].iloc[-2])
                macd_bullish = (df['macd_line'].iloc[-1] > df['macd_signal'].iloc[-1] and
                            df['macd_line'].iloc[-1] > df['macd_line'].iloc[-2])
                
                # CONFIRMACIÓN 2: RSI en zona favorable (flexible)
                rsi = df['rsi'].iloc[-1]
                rsi_favorable = 35 <= rsi <= 65 and rsi > df['rsi'].iloc[-2]
                
                # CONFIRMACIÓN 3: Precio rebotando desde EMA_50
                price_bouncing = (price > ema_50 * 0.998 and 
                                price > df['close'].iloc[-2])
                
                # Al menos 2 de 3 confirmaciones
                confirmations = [
                    macd_cross_up or macd_bullish,
                    rsi_favorable,
                    price_bouncing
                ]
                
                if sum(confirmations) >= 2:
                    return 'long'

        # --- 3. Lógica SHORT (Pullback en tendencia bajista) ---
        if is_strong_downtrend:
            # Pullback: precio cerca o tocó EMA_50 en últimas 5 velas
            pullback_detected = (df['high'].iloc[-5:] >= ema_50 * 0.995).any()
            
            if pullback_detected:
                # CONFIRMACIÓN 1: MACD cruzando a la baja O bajista con momentum
                macd_cross_down = (df['macd_line'].iloc[-1] < df['macd_signal'].iloc[-1] and 
                                df['macd_line'].iloc[-2] >= df['macd_signal'].iloc[-2])
                macd_bearish = (df['macd_line'].iloc[-1] < df['macd_signal'].iloc[-1] and
                            df['macd_line'].iloc[-1] < df['macd_line'].iloc[-2])
                
                # CONFIRMACIÓN 2: RSI en zona favorable (flexible)
                rsi = df['rsi'].iloc[-1]
                rsi_favorable = 35 <= rsi <= 65 and rsi < df['rsi'].iloc[-2]
                
                # CONFIRMACIÓN 3: Precio rechazando desde EMA_50
                price_rejecting = (price < ema_50 * 1.002 and 
                                price < df['close'].iloc[-2])
                
                # Al menos 2 de 3 confirmaciones
                confirmations = [
                    macd_cross_down or macd_bearish,
                    rsi_favorable,
                    price_rejecting
                ]
                
                if sum(confirmations) >= 2:
                    return 'short'

        return None

    @staticmethod
    def strategy_candle_pattern_reversal(df, lookback=200):
        """
        Estrategia FOREX FLEXIBLE de reversión con patrones de velas en niveles clave.
        Optimizada para generar señales de calidad con filtros inteligentes.
        
        Args:
            df (DataFrame): DataFrame con datos OHLC y indicadores
            lookback (int): Periodo de lookback para niveles (200 velas)
        
        Returns:
            str: 'long', 'short' o None
        """
        
        # Configuración específica para EURUSD
        pair = "EURUSD"
        pair_settings = {
            "tolerance_base": 0.002,  # 0.2% (más flexible)
            "rsi_overbought": 65,  # Menos restrictivo
            "rsi_oversold": 35,    # Menos restrictivo
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
        
        # 2. DETECCIÓN DE SOPORTES/RESISTENCIAS
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
        
        # Método 2: Mínimos y máximos locales
        window_size = max(10, lookback // 20)
        supports = []
        resistances = []
        
        for i in range(window_size, len(recent_data) - window_size, window_size // 2):
            window = recent_data.iloc[i-window_size:i+window_size]
            
            if window['low'].iloc[window_size] == window['low'].min():
                supports.append(window['low'].iloc[window_size])
            
            if window['high'].iloc[window_size] == window['high'].max():
                resistances.append(window['high'].iloc[window_size])
        
        # Método 3: Niveles psicológicos
        psychological_levels = []
        base_level = round(current_price, 3)
        for i in range(-5, 6):
            level = base_level + (i * 0.005)
            psychological_levels.append(level)
        
        # Combinar todos los niveles
        all_supports = supports + [s1, s2] + [l for l in psychological_levels if l < current_price]
        all_resistances = resistances + [r1, r2] + [l for l in psychological_levels if l > current_price]
        
        # Encontrar niveles más relevantes
        support = max(all_supports, key=lambda x: sum(abs(recent_data['low'] - x) < 0.0005)) if all_supports else daily_low
        resistance = min(all_resistances, key=lambda x: sum(abs(recent_data['high'] - x) < 0.0005)) if all_resistances else daily_high
        
        # 3. TOLERANCIA ADAPTATIVA
        atr = df['atr'].iloc[-1]
        volatility_ratio = atr / current_price
        
        if volatility_ratio > pair_settings["volatility_threshold"]:
            tolerance = min(pair_settings["tolerance_base"] * 1.5, atr * pair_settings["min_atr_multiplier"])
        else:
            tolerance = max(pair_settings["tolerance_base"], atr * pair_settings["min_atr_multiplier"] * 0.8)
        
        tolerance = min(tolerance, pair_settings["tolerance_base"] * 2)
        
        # 4. DETECCIÓN DE PATRONES DE VELAS
        candle_data = df.to_dict('records')
        current_index = len(candle_data) - 1
        
        try:
            signals = CandlePatterns.detect_all_patterns(candle_data, current_index)
        except:
            signals = {'long': [], 'short': [], 'neutral': []}
        
        # 5. INDICADORES DE CONFIRMACIÓN
        rsi = df['rsi'].iloc[-1]
        rsi_prev = df['rsi'].iloc[-2] if len(df) > 1 else rsi
        
        # Volumen relativo (si disponible)
        volume_increase = False
        if 'tick_volume' in df.columns and len(df) > 20:
            avg_volume = df['tick_volume'].iloc[-50:].mean()
            current_volume = df['tick_volume'].iloc[-1]
            volume_increase = current_volume > avg_volume * 1.2  # Menos restrictivo
        
        # Momentum adicional
        price_above_ema = False
        if 'ema_20' in df.columns:
            price_above_ema = df['close'].iloc[-1] > df['ema_20'].iloc[-1]
        
        # 6. EVALUACIÓN LONG
        distance_to_support = abs(df['low'].iloc[-1] - support) / support
        is_near_support = distance_to_support < tolerance
        
        # Patrones alcistas con pesos
        bullish_weights = {
            'hammer': 2, 'inverted_hammer': 2, 'bullish_engulfing': 3,
            'piercing_line': 2, 'morning_star': 3, 'three_white_soldiers': 3,
            'doji_dragonfly': 1
        }
        
        has_bullish_pattern = any(pattern in signals['long'] for pattern in bullish_weights.keys())
        bullish_pattern_strength = sum(bullish_weights.get(pattern, 1) for pattern in signals['long'] if pattern in bullish_weights)
        
        # Condiciones adicionales
        has_doji_at_support = 'doji' in signals['neutral'] and is_near_support
        rsi_oversold = rsi < pair_settings["rsi_oversold"] and rsi > rsi_prev
        price_confirmation = df['close'].iloc[-1] > df['open'].iloc[-1]
        strong_bullish_candle = (df['close'].iloc[-1] - df['open'].iloc[-1]) > (atr * 0.25)
        
        # SCORE LONG (menos restrictivo)
        long_score = 0
        if is_near_support: long_score += 2
        if has_bullish_pattern: long_score += bullish_pattern_strength
        if has_doji_at_support: long_score += 1
        if rsi_oversold: long_score += 2
        if volume_increase: long_score += 1
        if price_confirmation: long_score += 1
        if strong_bullish_candle: long_score += 1
        if price_above_ema: long_score += 1
        
        # 7. EVALUACIÓN SHORT
        distance_to_resistance = abs(df['high'].iloc[-1] - resistance) / resistance
        is_near_resistance = distance_to_resistance < tolerance
        
        # Patrones bajistas con pesos
        bearish_weights = {
            'shooting_star': 2, 'hanging_man': 2, 'bearish_engulfing': 3,
            'dark_cloud_cover': 2, 'evening_star': 3, 'three_black_crows': 3,
            'doji_gravestone': 1
        }
        
        has_bearish_pattern = any(pattern in signals['short'] for pattern in bearish_weights.keys())
        bearish_pattern_strength = sum(bearish_weights.get(pattern, 1) for pattern in signals['short'] if pattern in bearish_weights)
        
        # Condiciones adicionales
        has_doji_at_resistance = 'doji' in signals['neutral'] and is_near_resistance
        rsi_overbought = rsi > pair_settings["rsi_overbought"] and rsi < rsi_prev
        price_confirmation_short = df['close'].iloc[-1] < df['open'].iloc[-1]
        strong_bearish_candle = (df['open'].iloc[-1] - df['close'].iloc[-1]) > (atr * 0.25)
        
        # SCORE SHORT (menos restrictivo)
        short_score = 0
        if is_near_resistance: short_score += 2
        if has_bearish_pattern: short_score += bearish_pattern_strength
        if has_doji_at_resistance: short_score += 1
        if rsi_overbought: short_score += 2
        if volume_increase: short_score += 1
        if price_confirmation_short: short_score += 1
        if strong_bearish_candle: short_score += 1
        if not price_above_ema: short_score += 1
        
        # 8. DECISIÓN FINAL (menos restrictivo)
        required_score = 3  # Score mínimo requerido
        
        # Evitar señales contradictorias
        if long_score >= required_score and long_score > short_score:
            if df['close'].iloc[-1] > df['close'].iloc[-2]:
                return 'long'
        
        if short_score >= required_score and short_score > long_score:
            if df['close'].iloc[-1] < df['close'].iloc[-2]:
                return 'short'
        
        return None

    @staticmethod
    def strategy_ma_crossover(df):
        """
        Estrategia de Cruce de Medias Móviles FLEXIBLE.
        
        Lógica:
        - Cruce de EMA rápida (10) y lenta (50)
        - FILTRO FLEXIBLE: Opera a favor de tendencia o cerca de EMA_200
        - LONG: Cruce alcista + condiciones favorables
        - SHORT: Cruce bajista + condiciones favorables
        """
        required = ['ema_fast', 'ema_slow', 'ema_200', 'close']
        if not all(col in df.columns for col in required):
            return None
        
        # Obtener valores actuales y previos
        ema_fast = df['ema_fast'].iloc[-1]
        ema_slow = df['ema_slow'].iloc[-1]
        ema_fast_prev = df['ema_fast'].iloc[-2]
        ema_slow_prev = df['ema_slow'].iloc[-2]
        ema_200 = df['ema_200'].iloc[-1]
        price = df['close'].iloc[-1]
        price_prev = df['close'].iloc[-2]
        
        # Filtro de tendencia FLEXIBLE (permite operaciones cerca de EMA_200)
        is_uptrend_or_neutral = price > ema_200 * 0.99  # 1% tolerancia
        is_downtrend_or_neutral = price < ema_200 * 1.01
        
        # Detectar cruce alcista
        cross_up = ema_fast > ema_slow and ema_fast_prev <= ema_slow_prev
        
        # Detectar cruce bajista
        cross_down = ema_fast < ema_slow and ema_fast_prev >= ema_slow_prev
        
        # Confirmaciones adicionales (más flexible)
        price_momentum_up = price > price_prev
        price_momentum_down = price < price_prev
        
        # RSI adicional si está disponible
        rsi_favorable_long = True
        rsi_favorable_short = True
        if 'rsi' in df.columns:
            rsi = df['rsi'].iloc[-1]
            rsi_favorable_long = rsi < 65  # No sobrecomprado
            rsi_favorable_short = rsi > 35  # No sobrevendido
        
        # LONG: Cruce alcista + tendencia favorable + confirmaciones
        if cross_up and is_uptrend_or_neutral:
            confirmations = [
                price_momentum_up,
                rsi_favorable_long,
                price > ema_200 * 0.995  # Cerca o sobre EMA_200
            ]
            if sum(confirmations) >= 2:  # 2 de 3
                return 'long'
        
        # SHORT: Cruce bajista + tendencia favorable + confirmaciones
        if cross_down and is_downtrend_or_neutral:
            confirmations = [
                price_momentum_down,
                rsi_favorable_short,
                price < ema_200 * 1.005  # Cerca o bajo EMA_200
            ]
            if sum(confirmations) >= 2:  # 2 de 3
                return 'short'
        
        return None

    @staticmethod
    def strategy_scalping_stochrsi_ema(df):
        """
        Estrategia de Scalping FLEXIBLE con StochRSI y EMAs.
        
        Lógica:
        - Usa StochRSI para momentum rápido
        - Filtro de tendencia FLEXIBLE
        - LONG: StochRSI favorable + tendencia alcista o neutral
        - SHORT: StochRSI favorable + tendencia bajista o neutral
        """
        required = ['close', 'stochrsi_k', 'stochrsi_d', 'ema_20', 'ema_50']
        if not all(col in df.columns for col in required):
            return None

        # Obtener valores actuales y previos
        close = df['close'].iloc[-1]
        stoch_k = df['stochrsi_k'].iloc[-1]
        stoch_d = df['stochrsi_d'].iloc[-1]
        stoch_k_prev = df['stochrsi_k'].iloc[-2] if len(df) > 1 else stoch_k
        stoch_d_prev = df['stochrsi_d'].iloc[-2] if len(df) > 1 else stoch_d
        ema_20 = df['ema_20'].iloc[-1]
        ema_50 = df['ema_50'].iloc[-1]
        
        # Verificar que los valores no sean NaN
        if pd.isna(stoch_k) or pd.isna(stoch_d) or pd.isna(ema_20) or pd.isna(ema_50):
            return None

        # Filtro de tendencia FLEXIBLE
        is_uptrend_or_neutral = close > ema_50 * 0.995 or (close > ema_20 * 0.998)
        is_downtrend_or_neutral = close < ema_50 * 1.005 or (close < ema_20 * 1.002)
        
        # Detectar cruce de StochRSI
        stoch_cross_up = stoch_k > stoch_d and stoch_k_prev <= stoch_d_prev
        stoch_cross_down = stoch_k < stoch_d and stoch_k_prev >= stoch_d_prev

        # Condiciones para LONG (más flexible)
        if is_uptrend_or_neutral:
            # StochRSI alcista y en zona favorable
            stoch_bullish = stoch_k > stoch_d and stoch_k < 80
            stoch_oversold_recovery = stoch_k > 25 and stoch_cross_up
            
            if stoch_bullish or stoch_oversold_recovery:
                return 'long'

        # Condiciones para SHORT (más flexible)
        if is_downtrend_or_neutral:
            # StochRSI bajista y en zona favorable
            stoch_bearish = stoch_k < stoch_d and stoch_k > 20
            stoch_overbought_reversal = stoch_k < 75 and stoch_cross_down
            
            if stoch_bearish or stoch_overbought_reversal:
                return 'short'

        return None

    @staticmethod
    def strategy_fibonacci_reversal(df, lookback=100):
        """
        Estrategia de Fibonacci FLEXIBLE con reversiones en niveles clave.
        
        Lógica:
        - Identifica niveles de Fibonacci en swing reciente
        - LONG: Precio en nivel Fib + patrón de reversión alcista
        - SHORT: Precio en nivel Fib + patrón de reversión bajista
        - Tolerancia ampliada para más señales
        """
        required = ['high', 'low', 'close']
        if not all(col in df.columns for col in required): 
            return None
        
        swing_high = df['high'].iloc[-lookback:-1].max()
        swing_low = df['low'].iloc[-lookback:-1].min()
        price_range = swing_high - swing_low
        
        if price_range == 0: 
            return None
        
        # Niveles de Fibonacci (añadimos más niveles)
        fib_levels = {
            'level_0.236': swing_high - 0.236 * price_range,
            'level_0.382': swing_high - 0.382 * price_range,
            'level_0.500': swing_high - 0.500 * price_range,
            'level_0.618': swing_high - 0.618 * price_range,
            'level_0.786': swing_high - 0.786 * price_range
        }
        
        candle_data = df.to_dict('records')
        try:
            signals = CandlePatterns.detect_all_patterns(candle_data)
        except:
            signals = {'long': [], 'short': [], 'neutral': []}
        
        current_price = df['close'].iloc[-1]
        current_low = df['low'].iloc[-1]
        current_high = df['high'].iloc[-1]
        
        # Patrones alcistas (ampliados)
        bullish_patterns = ['hammer', 'bullish_engulfing', 'piercing_line', 'morning_star', 'doji']
        has_bullish_pattern = any(pattern in signals['long'] or pattern in signals['neutral'] for pattern in bullish_patterns)
        
        # RSI adicional si está disponible
        rsi_favorable_long = True
        if 'rsi' in df.columns:
            rsi = df['rsi'].iloc[-1]
            rsi_favorable_long = rsi < 60  # Flexible
        
        # LONG: Cerca de nivel Fibonacci + patrón alcista
        for level in fib_levels.values():
            distance = abs(current_low - level) / level
            if distance < 0.015 and has_bullish_pattern and rsi_favorable_long:  # 1.5% tolerancia
                return 'long'
        
        # Niveles para SHORT (desde swing low)
        fib_levels_short = {
            'level_0.236': swing_low + 0.236 * price_range,
            'level_0.382': swing_low + 0.382 * price_range,
            'level_0.500': swing_low + 0.500 * price_range,
            'level_0.618': swing_low + 0.618 * price_range,
            'level_0.786': swing_low + 0.786 * price_range
        }
        
        # Patrones bajistas (ampliados)
        bearish_patterns = ['shooting_star', 'bearish_engulfing', 'dark_cloud_cover', 'evening_star', 'doji']
        has_bearish_pattern = any(pattern in signals['short'] or pattern in signals['neutral'] for pattern in bearish_patterns)
        
        # RSI adicional
        rsi_favorable_short = True
        if 'rsi' in df.columns:
            rsi_favorable_short = rsi > 40  # Flexible
        
        # SHORT: Cerca de nivel Fibonacci + patrón bajista
        for level in fib_levels_short.values():
            distance = abs(current_high - level) / level
            if distance < 0.015 and has_bearish_pattern and rsi_favorable_short:  # 1.5% tolerancia
                return 'short'
        
        return None

    @staticmethod
    def strategy_chart_pattern_breakout(df, lookback=60):
        """
        Estrategia de Patrones Gráficos FLEXIBLE (Rompimientos).
        
        Lógica:
        - Detecta doble techo/suelo con tolerancia flexible
        - LONG: Rompimiento alcista de doble suelo
        - SHORT: Rompimiento bajista de doble techo
        """
        if len(df) < lookback or 'atr' not in df.columns:
            return None

        df_lookback = df.iloc[-lookback:]
        prominence = df_lookback['atr'].iloc[-1] * 1.2  # Menos restrictivo

        peaks, _ = find_peaks(df_lookback['high'], prominence=prominence)
        valleys, _ = find_peaks(-df_lookback['low'], prominence=prominence)

        # SHORT: Doble techo con tolerancia flexible
        if len(peaks) >= 2:
            p1_idx, p2_idx = peaks[-2], peaks[-1]
            p1_high, p2_high = df_lookback['high'].iloc[p1_idx], df_lookback['high'].iloc[p2_idx]

            if abs(p1_high - p2_high) / p1_high < 0.04:  # 4% tolerancia
                neckline = df_lookback['low'].iloc[p1_idx:p2_idx].min()
                
                # Confirmación de rompimiento
                current_close = df_lookback['close'].iloc[-1]
                prev_close = df_lookback['close'].iloc[-2]
                
                if current_close < neckline * 0.998 and prev_close >= neckline * 0.998:
                    # Confirmación adicional con RSI
                    if 'rsi' in df.columns:
                        rsi = df['rsi'].iloc[-1]
                        if rsi > 40:  # No sobrevendido extremo
                            return 'short'
                    else:
                        return 'short'

        # LONG: Doble suelo con tolerancia flexible
        if len(valleys) >= 2:
            v1_idx, v2_idx = valleys[-2], valleys[-1]
            v1_low, v2_low = df_lookback['low'].iloc[v1_idx], df_lookback['low'].iloc[v2_idx]

            if abs(v1_low - v2_low) / v1_low < 0.04:  # 4% tolerancia
                neckline = df_lookback['high'].iloc[v1_idx:v2_idx].max()
                
                # Confirmación de rompimiento
                current_close = df_lookback['close'].iloc[-1]
                prev_close = df_lookback['close'].iloc[-2]
                
                if current_close > neckline * 1.002 and prev_close <= neckline * 1.002:
                    # Confirmación adicional con RSI
                    if 'rsi' in df.columns:
                        rsi = df['rsi'].iloc[-1]
                        if rsi < 60:  # No sobrecomprado extremo
                            return 'long'
                    else:
                        return 'long'

        return None

    @staticmethod
    def strategy_hybrid_optimizer(df, min_score=3):
        """
        Estrategia híbrida FLEXIBLE que combina múltiples señales.
        Usa sistema de puntuación para filtrar oportunidades de calidad.
        """
        if len(df) < 200:
            return None
            
        # Inicializar puntuación
        long_score = 0
        short_score = 0
        
        # 1. TENDENCIA PRINCIPAL (EMA 50 y 200) - Flexible
        if 'ema_50' in df.columns and 'ema_200' in df.columns:
            ema_50 = df['ema_50'].iloc[-1]
            ema_200 = df['ema_200'].iloc[-1]
            price = df['close'].iloc[-1]
            
            if ema_50 > ema_200 * 1.001 and price > ema_50 * 0.995:
                long_score += 2
            elif ema_50 < ema_200 * 0.999 and price < ema_50 * 1.005:
                short_score += 2
                
        # 2. MOMENTUM (RSI + MACD) - Flexible
        if 'rsi' in df.columns:
            rsi = df['rsi'].iloc[-1]
            rsi_prev = df['rsi'].iloc[-2]
            
            if 30 < rsi < 55 and rsi > rsi_prev:
                long_score += 1.5
            elif 45 < rsi < 70 and rsi < rsi_prev:
                short_score += 1.5
                
        if 'macd_line' in df.columns and 'macd_signal' in df.columns:
            macd = df['macd_line'].iloc[-1]
            signal = df['macd_signal'].iloc[-1]
            macd_prev = df['macd_line'].iloc[-2]
            signal_prev = df['macd_signal'].iloc[-2]
            
            # Cruce O posición con momentum
            if (macd > signal and macd_prev <= signal_prev) or (macd > signal and macd > macd_prev):
                long_score += 2
            elif (macd < signal and macd_prev >= signal_prev) or (macd < signal and macd < macd_prev):
                short_score += 2
                
        # 3. VOLATILIDAD (Bollinger Bands + ATR)
        if all(col in df.columns for col in ['bb_upper', 'bb_lower', 'atr']):
            close = df['close'].iloc[-1]
            bb_upper = df['bb_upper'].iloc[-1]
            bb_lower = df['bb_lower'].iloc[-1]
            bb_middle = (bb_upper + bb_lower) / 2
            
            bb_position = (close - bb_lower) / (bb_upper - bb_lower) if (bb_upper - bb_lower) > 0 else 0.5
            
            if 0.15 < bb_position < 0.45:  # Zona inferior-media
                long_score += 1
            elif 0.55 < bb_position < 0.85:  # Zona superior-media
                short_score += 1
                
        # 4. ESTRUCTURA DE MERCADO
        lookback = min(100, len(df) - 1)
        recent_highs = df['high'].iloc[-lookback:].rolling(10).max()
        recent_lows = df['low'].iloc[-lookback:].rolling(10).min()
        
        current_high = df['high'].iloc[-1]
        current_low = df['low'].iloc[-1]
        prev_high = recent_highs.iloc[-10] if len(recent_highs) > 10 else df['high'].iloc[-2]
        prev_low = recent_lows.iloc[-10] if len(recent_lows) > 10 else df['low'].iloc[-2]
        
        if current_high > prev_high * 1.001:
            long_score += 1
        if current_low < prev_low * 0.999:
            short_score += 1
            
        # 5. PATRONES DE VELAS (simplificado)
        candle_data = df.to_dict('records')
        current_index = len(candle_data) - 1
        try:
            signals = CandlePatterns.detect_all_patterns(candle_data, current_index)
            
            strong_bullish = ['bullish_engulfing', 'morning_star', 'hammer']
            strong_bearish = ['bearish_engulfing', 'evening_star', 'shooting_star']
            
            if any(pattern in signals['long'] for pattern in strong_bullish):
                long_score += 1.5
            if any(pattern in signals['short'] for pattern in strong_bearish):
                short_score += 1.5
        except:
            pass
            
        # 6. CONFIRMACIÓN DE VOLUMEN
        if 'tick_volume' in df.columns and len(df) > 20:
            current_vol = df['tick_volume'].iloc[-1]
            avg_vol = df['tick_volume'].iloc[-20:].mean()
            
            if current_vol > avg_vol * 1.2:
                if df['close'].iloc[-1] > df['open'].iloc[-1]:
                    long_score += 1
                else:
                    short_score += 1
                    
        # 7. FILTRO FINAL (más flexible)
        if long_score >= min_score and long_score > short_score:
            return 'long'
        elif short_score >= min_score and short_score > long_score:
            return 'short'
            
        return None

    @staticmethod
    def strategy_ichimoku_kinko_hyo(df):
        """
        Estrategia Ichimoku Kinko Hyo FLEXIBLE para máxima rentabilidad.
        
        Lógica:
        - Analiza la posición del precio respecto a la nube (Kumo)
        - Confirma señales con cruce de Tenkan-sen y Kijun-sen
        - Filtros inteligentes pero no excesivamente restrictivos
        - LONG: Precio sobre nube + condiciones favorables
        - SHORT: Precio bajo nube + condiciones favorables
        """
        required = ['close', 'tenkan_sen', 'kijun_sen', 'senkou_span_a', 'senkou_span_b']
        if not all(col in df.columns for col in required):
            return None
        
        # Verificar que tenemos suficientes datos
        if len(df) < 26:  # Ichimoku necesita al menos 26 períodos
            return None
        
        # --- 1. Obtener valores actuales y previos ---
        price = df['close'].iloc[-1]
        price_prev = df['close'].iloc[-2]
        tenkan_sen = df['tenkan_sen'].iloc[-1]
        kijun_sen = df['kijun_sen'].iloc[-1]
        tenkan_sen_prev = df['tenkan_sen'].iloc[-2]
        kijun_sen_prev = df['kijun_sen'].iloc[-2]
        senkou_span_a = df['senkou_span_a'].iloc[-1]
        senkou_span_b = df['senkou_span_b'].iloc[-1]
        
        # --- 2. Definir posición respecto a la nube (Kumo) ---
        kumo_top = max(senkou_span_a, senkou_span_b)
        kumo_bottom = min(senkou_span_a, senkou_span_b)
        
        # Posición del precio respecto a la nube
        is_above_kumo = price > kumo_top * 0.998  # Tolerancia 0.2%
        is_below_kumo = price < kumo_bottom * 1.002
        is_inside_kumo = not is_above_kumo and not is_below_kumo
        
        # --- 3. Detectar cruces y posiciones de Tenkan-sen y Kijun-sen ---
        tk_cross_up = tenkan_sen > kijun_sen and tenkan_sen_prev <= kijun_sen_prev
        tk_cross_down = tenkan_sen < kijun_sen and tenkan_sen_prev >= kijun_sen_prev
        tk_bullish = tenkan_sen > kijun_sen
        tk_bearish = tenkan_sen < kijun_sen
        
        # --- 4. Confirmaciones adicionales FLEXIBLES ---
        
        # Momentum del precio
        price_momentum_up = price > price_prev
        price_momentum_down = price < price_prev
        
        # Dirección de las líneas Ichimoku
        tenkan_rising = tenkan_sen > tenkan_sen_prev
        kijun_rising = kijun_sen > kijun_sen_prev
        tenkan_falling = tenkan_sen < tenkan_sen_prev
        kijun_falling = kijun_sen < kijun_sen_prev
        
        # Distancia del precio a la nube (flexible)
        if is_above_kumo:
            distance_ratio = abs(price - kumo_top) / price
        elif is_below_kumo:
            distance_ratio = abs(price - kumo_bottom) / price
        else:
            distance_ratio = 0
        
        # RSI adicional si está disponible
        rsi_favorable_long = True
        rsi_favorable_short = True
        if 'rsi' in df.columns:
            rsi = df['rsi'].iloc[-1]
            rsi_prev = df['rsi'].iloc[-2]
            rsi_favorable_long = rsi < 60 and rsi > rsi_prev  # Flexible
            rsi_favorable_short = rsi > 40 and rsi < rsi_prev
        
        # --- 5. LÓGICA LONG FLEXIBLE ---
        if is_above_kumo:
            # Confirmaciones: cruce O posición alcista con momentum
            confirmations = 0
            
            # Confirmación 1: Tenkan/Kijun alcistas
            if tk_cross_up or (tk_bullish and tenkan_rising):
                confirmations += 1
            
            # Confirmación 2: Precio con momentum alcista
            if price_momentum_up:
                confirmations += 1
            
            # Confirmación 3: Líneas subiendo
            if tenkan_rising or kijun_rising:
                confirmations += 1
            
            # Confirmación 4: RSI favorable
            if rsi_favorable_long:
                confirmations += 1
            
            # Confirmación 5: Precio claramente sobre nube (no muy lejos)
            if distance_ratio < 0.015:  # Dentro de 1.5%
                confirmations += 1
            
            # Requerir al menos 3 de 5 confirmaciones (60%)
            if confirmations >= 3:
                return 'long'
        
        # --- 6. LÓGICA SHORT FLEXIBLE ---
        if is_below_kumo:
            # Confirmaciones: cruce O posición bajista con momentum
            confirmations = 0
            
            # Confirmación 1: Tenkan/Kijun bajistas
            if tk_cross_down or (tk_bearish and tenkan_falling):
                confirmations += 1
            
            # Confirmación 2: Precio con momentum bajista
            if price_momentum_down:
                confirmations += 1
            
            # Confirmación 3: Líneas bajando
            if tenkan_falling or kijun_falling:
                confirmations += 1
            
            # Confirmación 4: RSI favorable
            if rsi_favorable_short:
                confirmations += 1
            
            # Confirmación 5: Precio claramente bajo nube (no muy lejos)
            if distance_ratio < 0.015:  # Dentro de 1.5%
                confirmations += 1
            
            # Requerir al menos 3 de 5 confirmaciones (60%)
            if confirmations >= 3:
                return 'short'
        
        # --- 7. SEÑALES DE ROMPIMIENTO DE NUBE (MÁS FLEXIBLE) ---
        
        # Rompimiento alcista: precio cruzando sobre la nube
        if (price > kumo_top and price_prev <= kumo_top * 1.005):
            # Confirmaciones para rompimiento
            breakout_confirmations = 0
            
            if tk_bullish or tk_cross_up:
                breakout_confirmations += 1
            if price_momentum_up:
                breakout_confirmations += 1
            if rsi_favorable_long:
                breakout_confirmations += 1
            
            # Al menos 2 de 3 para rompimiento alcista
            if breakout_confirmations >= 2:
                return 'long'
        
        # Rompimiento bajista: precio cruzando bajo la nube
        if (price < kumo_bottom and price_prev >= kumo_bottom * 0.995):
            # Confirmaciones para rompimiento
            breakout_confirmations = 0
            
            if tk_bearish or tk_cross_down:
                breakout_confirmations += 1
            if price_momentum_down:
                breakout_confirmations += 1
            if rsi_favorable_short:
                breakout_confirmations += 1
            
            # Al menos 2 de 3 para rompimiento bajista
            if breakout_confirmations >= 2:
                return 'short'
        
        return None
