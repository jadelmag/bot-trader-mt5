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
        Estrategia de Price Action con Soporte/Resistencia OPTIMIZADA.
        
        Mejoras:
        - Detección más precisa de zonas S/R
        - Confirmación con momentum real
        - Filtro de tendencia más estricto
        - Requiere TODAS las condiciones
        """
        required = ['low', 'high', 'close', 'open', 'ema_200', 'rsi', 'momentum']
        if not all(col in df.columns for col in required) or len(df) < lookback:
            return None

        # --- 1. Datos actuales ---
        price = df['close'].iloc[-1]
        price_prev = df['close'].iloc[-2]
        open_price = df['open'].iloc[-1]
        ema_200 = df['ema_200'].iloc[-1]
        rsi = df['rsi'].iloc[-1]
        rsi_prev = df['rsi'].iloc[-2]
        momentum = df['momentum'].iloc[-1]
        momentum_prev = df['momentum'].iloc[-2]
        
        # Tendencia ESTRICTA
        is_uptrend = price > ema_200 * 1.002  # 0.2% por encima
        is_downtrend = price < ema_200 * 0.998  # 0.2% por debajo
        
        # Si no hay tendencia clara, NO operar
        if not is_uptrend and not is_downtrend:
            return None

        # --- 2. Identificar Zonas S/R ---
        recent_data = df.iloc[-lookback:]
        
        # Zonas exclusivas (no solapadas)
        support_zone_top = recent_data['low'].quantile(0.30)
        support_zone_bottom = recent_data['low'].quantile(0.10)
        
        resistance_zone_bottom = recent_data['high'].quantile(0.70)
        resistance_zone_top = recent_data['high'].quantile(0.90)

        # --- 3. Momentum mínimo requerido ---
        min_momentum = abs(price * 0.00005)
        
        # --- 4. LONG: Solo en 30% inferior ---
        in_support_zone = support_zone_bottom <= price <= support_zone_top
        
        if is_uptrend and in_support_zone:
            # Confirmación de reversión con 3 velas
            if len(df) >= 3:
                price_3_ago = df['close'].iloc[-3]
                price_2_ago = df['close'].iloc[-2]
                bullish_reversal = price_3_ago > price_2_ago and price_2_ago < price_prev and price > price_prev
            else:
                bullish_reversal = price > price_prev and (price > open_price)
            
            # REQUIERE TODAS
            if (rsi < 40 and rsi > rsi_prev and  # RSI saliendo de sobreventa
                not pd.isna(momentum) and momentum > min_momentum and momentum > momentum_prev and
                bullish_reversal):
                return 'long'
        
        # --- 5. SHORT: Solo en 30% superior ---
        in_resistance_zone = resistance_zone_bottom <= price <= resistance_zone_top
        
        if is_downtrend and in_resistance_zone:
            # Confirmación de reversión con 3 velas
            if len(df) >= 3:
                price_3_ago = df['close'].iloc[-3]
                price_2_ago = df['close'].iloc[-2]
                bearish_reversal = price_3_ago < price_2_ago and price_2_ago > price_prev and price < price_prev
            else:
                bearish_reversal = price < price_prev and (price < open_price)
            
            # REQUIERE TODAS
            if (rsi > 60 and rsi < rsi_prev and  # RSI saliendo de sobrecompra
                not pd.isna(momentum) and momentum < -min_momentum and momentum < momentum_prev and
                bearish_reversal):
                return 'short'

        return None

    @staticmethod
    def strategy_ma_crossover(df):
        """
        Estrategia de Cruce de Medias Móviles OPTIMIZADA.
        
        Mejoras:
        - Requiere tendencia FUERTE en EMA_200
        - Cruce REAL con separación mínima
        - Confirmación con momentum consistente
        - RSI en zona favorable
        """
        required = ['close', 'ema_fast', 'ema_slow', 'ema_200', 'rsi', 'momentum']
        if not all(col in df.columns for col in required) or len(df) < 200:
            return None
        
        # Alias para compatibilidad
        if 'ema_fast' not in df.columns and 'EMA_10' in df.columns:
            df['ema_fast'] = df['EMA_10']
        if 'ema_slow' not in df.columns and 'EMA_50' in df.columns:
            df['ema_slow'] = df['EMA_50']
        
        # Datos actuales
        price = df['close'].iloc[-1]
        ema_fast = df['ema_fast'].iloc[-1]
        ema_slow = df['ema_slow'].iloc[-1]
        ema_fast_prev = df['ema_fast'].iloc[-2]
        ema_slow_prev = df['ema_slow'].iloc[-2]
        ema_200 = df['ema_200'].iloc[-1]
        rsi = df['rsi'].iloc[-1]
        rsi_prev = df['rsi'].iloc[-2]
        momentum = df['momentum'].iloc[-1]
        momentum_prev = df['momentum'].iloc[-2]
        
        # Tolerancia y momentum mínimo
        tolerance = abs(price * 0.00001)
        min_momentum = abs(price * 0.00005)
        
        # Verificar momentum consistente
        recent_momentum = df['momentum'].iloc[-5:].values
        positive_count = sum(m > 0 for m in recent_momentum if not pd.isna(m))
        negative_count = sum(m < 0 for m in recent_momentum if not pd.isna(m))
        
        # === LONG: Cruce alcista ===
        # Tendencia FUERTE alcista
        if price > ema_200 * 1.005:  # 0.5% por encima (FUERTE)
            # Cruce REAL: EMA rápida cruza hacia arriba la lenta
            golden_cross = (
                ema_fast > ema_slow and 
                ema_fast_prev <= ema_slow_prev and
                (ema_fast - ema_slow) > tolerance  # Separación real
            )
            
            if golden_cross:
                # Confirmaciones adicionales
                rsi_ok = 35 <= rsi <= 65 and rsi > rsi_prev
                momentum_ok = (not pd.isna(momentum) and 
                              momentum > min_momentum and 
                              momentum > momentum_prev)
                price_above_ema = price > ema_200
                momentum_consistent = positive_count >= 3
                
                # REQUIERE 3 de 4 confirmaciones
                confirmations = [rsi_ok, momentum_ok, price_above_ema, momentum_consistent]
                if sum(confirmations) >= 3:
                    return 'long'
        
        # === SHORT: Cruce bajista ===
        # Tendencia FUERTE bajista
        if price < ema_200 * 0.995:  # 0.5% por debajo (FUERTE)
            # Cruce REAL: EMA rápida cruza hacia abajo la lenta
            death_cross = (
                ema_fast < ema_slow and 
                ema_fast_prev >= ema_slow_prev and
                (ema_slow - ema_fast) > tolerance  # Separación real
            )
            
            if death_cross:
                # Confirmaciones adicionales
                rsi_ok = 35 <= rsi <= 65 and rsi < rsi_prev
                momentum_ok = (not pd.isna(momentum) and 
                              momentum < -min_momentum and 
                              momentum < momentum_prev)
                price_below_ema = price < ema_200
                momentum_consistent = negative_count >= 3
                
                # REQUIERE 3 de 4 confirmaciones
                confirmations = [rsi_ok, momentum_ok, price_below_ema, momentum_consistent]
                if sum(confirmations) >= 3:
                    return 'short'
        
        return None

    @staticmethod
    def strategy_scalping_stochrsi_ema(df):
        """
        Estrategia de Scalping OPTIMIZADA con StochRSI y EMA.
        
        Mejoras:
        - Requiere tendencia clara en EMA_20
        - StochRSI en zonas EXTREMAS (no >80/<20)
        - Cruce REAL confirmado
        - Momentum consistente
        - Precio confirmando dirección
        """
        required = ['close', 'ema_20', 'stochrsi_k', 'stochrsi_d', 'rsi', 'momentum']
        if not all(col in df.columns for col in required) or len(df) < 50:
            return None
        
        # Datos actuales
        price = df['close'].iloc[-1]
        price_prev = df['close'].iloc[-2]
        ema_20 = df['ema_20'].iloc[-1]
        stoch_k = df['stochrsi_k'].iloc[-1]
        stoch_d = df['stochrsi_d'].iloc[-1]
        stoch_k_prev = df['stochrsi_k'].iloc[-2]
        stoch_d_prev = df['stochrsi_d'].iloc[-2]
        rsi = df['rsi'].iloc[-1]
        rsi_prev = df['rsi'].iloc[-2]
        momentum = df['momentum'].iloc[-1]
        momentum_prev = df['momentum'].iloc[-2]
        
        # Verificar NaN
        if pd.isna(stoch_k) or pd.isna(stoch_d) or pd.isna(ema_20):
            return None
        
        # Momentum mínimo
        min_momentum = abs(price * 0.00005)
        
        # Verificar momentum consistente
        recent_momentum = df['momentum'].iloc[-5:].values
        positive_count = sum(m > 0 for m in recent_momentum if not pd.isna(m))
        negative_count = sum(m < 0 for m in recent_momentum if not pd.isna(m))
        
        # === LONG: StochRSI saliendo de sobreventa ===
        # Tendencia alcista
        if price > ema_20 * 1.001:  # 0.1% por encima
            # StochRSI en zona EXTREMA de sobreventa
            in_oversold = stoch_k < 15 and stoch_d < 15  # Más estricto (antes 20)
            
            # Cruce alcista REAL
            bullish_cross = (
                stoch_k > stoch_d and 
                stoch_k_prev <= stoch_d_prev and
                stoch_k > stoch_k_prev  # K subiendo
            )
            
            if in_oversold or bullish_cross:
                # Confirmaciones
                rsi_ok = rsi < 55 and rsi > rsi_prev
                momentum_ok = (not pd.isna(momentum) and 
                              momentum > min_momentum and 
                              momentum > momentum_prev)
                price_rising = price > price_prev
                momentum_consistent = positive_count >= 3
                
                # REQUIERE 3 de 4
                confirmations = [rsi_ok, momentum_ok, price_rising, momentum_consistent]
                if sum(confirmations) >= 3:
                    return 'long'
        
        # === SHORT: StochRSI saliendo de sobrecompra ===
        # Tendencia bajista
        if price < ema_20 * 0.999:  # 0.1% por debajo
            # StochRSI en zona EXTREMA de sobrecompra
            in_overbought = stoch_k > 85 and stoch_d > 85  # Más estricto (antes 80)
            
            # Cruce bajista REAL
            bearish_cross = (
                stoch_k < stoch_d and 
                stoch_k_prev >= stoch_d_prev and
                stoch_k < stoch_k_prev  # K bajando
            )
            
            if in_overbought or bearish_cross:
                # Confirmaciones
                rsi_ok = rsi > 45 and rsi < rsi_prev
                momentum_ok = (not pd.isna(momentum) and 
                              momentum < -min_momentum and 
                              momentum < momentum_prev)
                price_falling = price < price_prev
                momentum_consistent = negative_count >= 3
                
                # REQUIERE 3 de 4
                confirmations = [rsi_ok, momentum_ok, price_falling, momentum_consistent]
                if sum(confirmations) >= 3:
                    return 'short'
        
        return None

    @staticmethod
    def strategy_fibonacci_reversal(df, lookback=100):
        """
        Estrategia de Retroceso Fibonacci OPTIMIZADA.
        
        Mejoras:
        - Niveles Fibonacci más precisos (38.2%, 50%, 61.8%)
        - Confirmación con momentum real
        - RSI en zonas extremas
        - Patrón de reversión confirmado
        """
        required = ['high', 'low', 'close', 'rsi', 'momentum']
        if not all(col in df.columns for col in required) or len(df) < lookback:
            return None
        
        # Datos recientes
        recent_data = df.iloc[-lookback:]
        price = df['close'].iloc[-1]
        price_prev = df['close'].iloc[-2]
        rsi = df['rsi'].iloc[-1]
        rsi_prev = df['rsi'].iloc[-2]
        momentum = df['momentum'].iloc[-1]
        momentum_prev = df['momentum'].iloc[-2]
        
        # Momentum mínimo
        min_momentum = abs(price * 0.00005)
        
        # Encontrar swing high y swing low
        swing_high = recent_data['high'].max()
        swing_low = recent_data['low'].min()
        
        # Calcular rango
        fib_range = swing_high - swing_low
        
        if fib_range <= 0:
            return None
        
        # Niveles Fibonacci
        fib_23_6 = swing_high - (fib_range * 0.236)
        fib_38_2 = swing_high - (fib_range * 0.382)
        fib_50_0 = swing_high - (fib_range * 0.500)
        fib_61_8 = swing_high - (fib_range * 0.618)
        fib_78_6 = swing_high - (fib_range * 0.786)
        
        # Tolerancia (1% del rango)
        tolerance = fib_range * 0.01
        
        # === LONG: Rebote en niveles Fibonacci ===
        # Verificar si está en zona de retroceso (38.2% - 61.8%)
        in_fib_zone_long = (fib_61_8 - tolerance <= price <= fib_38_2 + tolerance)
        
        # Nivel más fuerte: 50%
        at_golden_level = abs(price - fib_50_0) < tolerance
        
        if in_fib_zone_long or at_golden_level:
            # Confirmación de reversión con 3 velas
            if len(df) >= 3:
                close_3_ago = df['close'].iloc[-3]
                close_2_ago = df['close'].iloc[-2]
                bullish_reversal = (close_3_ago > close_2_ago > price_prev and 
                                   price > price_prev)
            else:
                bullish_reversal = price > price_prev
            
            # Confirmaciones
            rsi_ok = rsi < 40 and rsi > rsi_prev  # Saliendo de sobreventa
            momentum_ok = (not pd.isna(momentum) and 
                          momentum > min_momentum and 
                          momentum > momentum_prev)
            
            # Bonus si está en nivel 50% o 61.8%
            at_strong_level = (abs(price - fib_50_0) < tolerance or 
                              abs(price - fib_61_8) < tolerance)
            
            # REQUIERE TODAS las confirmaciones básicas
            if bullish_reversal and rsi_ok and momentum_ok:
                return 'long'
        
        # === SHORT: Rechazo en niveles Fibonacci ===
        # Verificar si está en zona de extensión (23.6% - 38.2%)
        in_fib_zone_short = (fib_38_2 - tolerance <= price <= fib_23_6 + tolerance)
        
        # O cerca del máximo
        at_resistance = abs(price - swing_high) < tolerance
        
        if in_fib_zone_short or at_resistance:
            # Confirmación de reversión con 3 velas
            if len(df) >= 3:
                close_3_ago = df['close'].iloc[-3]
                close_2_ago = df['close'].iloc[-2]
                bearish_reversal = (close_3_ago < close_2_ago < price_prev and 
                                   price < price_prev)
            else:
                bearish_reversal = price < price_prev
            
            # Confirmaciones
            rsi_ok = rsi > 60 and rsi < rsi_prev  # Saliendo de sobrecompra
            momentum_ok = (not pd.isna(momentum) and 
                          momentum < -min_momentum and 
                          momentum < momentum_prev)
            
            # REQUIERE TODAS las confirmaciones básicas
            if bearish_reversal and rsi_ok and momentum_ok:
                return 'short'
        
        return None

    @staticmethod
    def strategy_ichimoku_kinko_hyo(df):
        """
        Estrategia Ichimoku Kinko Hyo OPTIMIZADA.
        
        Mejoras:
        - Requiere TODAS las 5 confirmaciones (no 3)
        - Cruce REAL de Tenkan/Kijun con separación
        - Momentum consistente
        - Posición clara respecto a la nube
        """
        required = ['close', 'high', 'low', 'momentum']
        if not all(col in df.columns for col in required) or len(df) < 52:
            return None
        
        # Calcular componentes Ichimoku
        # Tenkan-sen (línea de conversión): (max9 + min9) / 2
        high_9 = df['high'].rolling(window=9).max()
        low_9 = df['low'].rolling(window=9).min()
        tenkan_sen = (high_9 + low_9) / 2
        
        # Kijun-sen (línea base): (max26 + min26) / 2
        high_26 = df['high'].rolling(window=26).max()
        low_26 = df['low'].rolling(window=26).min()
        kijun_sen = (high_26 + low_26) / 2
        
        # Senkou Span A (línea adelantada A): (Tenkan + Kijun) / 2, desplazada 26 periodos
        senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(26)
        
        # Senkou Span B (línea adelantada B): (max52 + min52) / 2, desplazada 26 periodos
        high_52 = df['high'].rolling(window=52).max()
        low_52 = df['low'].rolling(window=52).min()
        senkou_span_b = ((high_52 + low_52) / 2).shift(26)
        
        # Datos actuales
        price = df['close'].iloc[-1]
        price_prev = df['close'].iloc[-2]
        tenkan = tenkan_sen.iloc[-1]
        kijun = kijun_sen.iloc[-1]
        tenkan_prev = tenkan_sen.iloc[-2]
        kijun_prev = kijun_sen.iloc[-2]
        span_a = senkou_span_a.iloc[-1]
        span_b = senkou_span_b.iloc[-1]
        momentum = df['momentum'].iloc[-1]
        momentum_prev = df['momentum'].iloc[-2]
        
        # Verificar NaN
        if any(pd.isna(x) for x in [tenkan, kijun, span_a, span_b]):
            return None
        
        # Tolerancia y momentum mínimo
        tolerance = abs(price * 0.00001)
        min_momentum = abs(price * 0.00005)
        
        # Verificar momentum consistente
        recent_momentum = df['momentum'].iloc[-5:].values
        positive_count = sum(m > 0 for m in recent_momentum if not pd.isna(m))
        negative_count = sum(m < 0 for m in recent_momentum if not pd.isna(m))
        
        # Nube (Kumo)
        cloud_top = max(span_a, span_b)
        cloud_bottom = min(span_a, span_b)
        
        # === LONG: Señal alcista ===
        # 1. Tenkan cruza Kijun hacia arriba (TK Cross)
        tk_cross_up = (tenkan > kijun and tenkan_prev <= kijun_prev and 
                       (tenkan - kijun) > tolerance)
        
        # 2. Precio por encima de la nube
        price_above_cloud = price > cloud_top * 1.001  # 0.1% por encima
        
        # 3. Nube es alcista (Span A > Span B)
        bullish_cloud = span_a > span_b
        
        # 4. Momentum positivo y consistente
        momentum_ok = (not pd.isna(momentum) and 
                      momentum > min_momentum and 
                      momentum > momentum_prev and
                      positive_count >= 4)  # 4 de 5 velas
        
        # 5. Precio subiendo
        price_rising = price > price_prev
        
        # REQUIERE TODAS las 5 confirmaciones
        if (tk_cross_up and price_above_cloud and bullish_cloud and 
            momentum_ok and price_rising):
            return 'long'
        
        # === SHORT: Señal bajista ===
        # 1. Tenkan cruza Kijun hacia abajo (TK Cross)
        tk_cross_down = (tenkan < kijun and tenkan_prev >= kijun_prev and 
                        (kijun - tenkan) > tolerance)
        
        # 2. Precio por debajo de la nube
        price_below_cloud = price < cloud_bottom * 0.999  # 0.1% por debajo
        
        # 3. Nube es bajista (Span A < Span B)
        bearish_cloud = span_a < span_b
        
        # 4. Momentum negativo y consistente
        momentum_ok = (not pd.isna(momentum) and 
                      momentum < -min_momentum and 
                      momentum < momentum_prev and
                      negative_count >= 4)  # 4 de 5 velas
        
        # 5. Precio bajando
        price_falling = price < price_prev
        
        # REQUIERE TODAS las 5 confirmaciones
        if (tk_cross_down and price_below_cloud and bearish_cloud and 
            momentum_ok and price_falling):
            return 'short'
        
        return None

    @staticmethod
    def strategy_bollinger_bands_breakout(df):
        """
        Estrategia Bollinger Bands MEAN REVERSION OPTIMIZADA.
        
        Mejoras:
        - Requiere reversión confirmada en 3 velas
        - RSI más estricto (zonas extremas)
        - Momentum debe ser consistente
        - Verificación de cierre dentro de bandas
        """
        required = ['close', 'bb_upper', 'bb_lower', 'high', 'low', 'rsi', 'momentum']
        if not all(col in df.columns for col in required) or len(df) < 20:
            return None
            
        # Datos actuales
        close = df['close'].iloc[-1]
        close_prev = df['close'].iloc[-2]
        high = df['high'].iloc[-1]
        low = df['low'].iloc[-1]
        bb_upper = df['bb_upper'].iloc[-1]
        bb_lower = df['bb_lower'].iloc[-1]
        rsi = df['rsi'].iloc[-1]
        rsi_prev = df['rsi'].iloc[-2]
        momentum = df['momentum'].iloc[-1]
        momentum_prev = df['momentum'].iloc[-2]
        
        # Momentum mínimo
        min_momentum = abs(close * 0.00005)
        
        # Verificar momentum consistente en 5 velas
        recent_momentum = df['momentum'].iloc[-5:].values
        positive_count = sum(m > 0 for m in recent_momentum if not pd.isna(m))
        negative_count = sum(m < 0 for m in recent_momentum if not pd.isna(m))
        
        # Reversión confirmada con 3 velas
        if len(df) >= 3:
            close_3_ago = df['close'].iloc[-3]
            close_2_ago = df['close'].iloc[-2]
            
            bullish_reversal_confirmed = (
                close_3_ago > close_2_ago > close_prev and  # 2 velas bajistas
                close > close_prev and  # Vela actual alcista
                close > close_3_ago  # Supera inicio
            )
            
            bearish_reversal_confirmed = (
                close_3_ago < close_2_ago < close_prev and  # 2 velas alcistas
                close < close_prev and  # Vela actual bajista
                close < close_3_ago  # Rompe inicio
            )
        else:
            bullish_reversal_confirmed = close > close_prev
            bearish_reversal_confirmed = close < close_prev
        
        # LONG: Banda inferior + RSI extremo + momentum
        if (low <= bb_lower and  # Tocó banda inferior
            close > bb_lower and  # Cerró dentro
            rsi < 35 and rsi > rsi_prev and  # RSI extremo saliendo
            not pd.isna(momentum) and momentum > min_momentum and
            momentum > momentum_prev and
            positive_count >= 3 and  # Momentum consistente
            bullish_reversal_confirmed):
            return 'long'
        
        # SHORT: Banda superior + RSI extremo + momentum
        if (high >= bb_upper and  # Tocó banda superior
            close < bb_upper and  # Cerró dentro
            rsi > 65 and rsi < rsi_prev and  # RSI extremo saliendo
            not pd.isna(momentum) and momentum < -min_momentum and
            momentum < momentum_prev and
            negative_count >= 3 and  # Momentum consistente
            bearish_reversal_confirmed):
            return 'short'
        
        return None

    @staticmethod
    def strategy_hybrid_optimizer(df):
        """
        Estrategia HÍBRIDA OPTIMIZADA que combina múltiples señales con scoring estricto.
        
        Lógica CORREGIDA:
        - Requiere puntuación mínima de 4 de 6 (antes era 3)
        - Verifica cruces MACD reales
        - Momentum debe ser consistente
        - Filtro de tendencia más estricto
        """
        required = ['close', 'rsi', 'macd_line', 'macd_signal', 'ema_50', 'ema_200', 'momentum']
        if not all(col in df.columns for col in required) or len(df) < 10:
            return None
        
        # Verificar suficientes velas
        if len(df) < 10:
            return None
        
        price = df['close'].iloc[-1]
        price_prev = df['close'].iloc[-2]
        rsi = df['rsi'].iloc[-1]
        rsi_prev = df['rsi'].iloc[-2]
        macd_line = df['macd_line'].iloc[-1]
        macd_signal = df['macd_signal'].iloc[-1]
        macd_line_prev = df['macd_line'].iloc[-2]
        macd_signal_prev = df['macd_signal'].iloc[-2]
        ema_50 = df['ema_50'].iloc[-1]
        ema_200 = df['ema_200'].iloc[-1]
        momentum = df['momentum'].iloc[-1]
        momentum_prev = df['momentum'].iloc[-2]
        
        # Verificar momentum consistente en 5 velas
        recent_momentum = df['momentum'].iloc[-5:].values
        positive_count = sum(m > 0 for m in recent_momentum if not pd.isna(m))
        negative_count = sum(m < 0 for m in recent_momentum if not pd.isna(m))
        
        # Sistema de puntuación estricto
        long_score = 0
        short_score = 0
        
        # Tolerancia para cruces MACD
        tolerance = abs(price * 0.00001)
        min_momentum = abs(price * 0.00005)
        
        # === CRITERIOS PARA LONG ===
        
        # 1. Tendencia alcista (peso: 1)
        if price > ema_200 * 1.002:  # 0.2% por encima
            long_score += 1
        
        # 2. RSI favorable (peso: 1)
        if 30 < rsi < 65 and rsi > rsi_prev:
            long_score += 1
        
        # 3. MACD cruce alcista REAL (peso: 1)
        if (macd_line > macd_signal and 
            macd_line_prev <= macd_signal_prev and
            (macd_line - macd_signal) > tolerance):
            long_score += 1
        
        # 4. Precio subiendo (peso: 1)
        if price > price_prev:
            long_score += 1
        
        # 5. Momentum positivo Y consistente (peso: 1)
        if (not pd.isna(momentum) and 
            momentum > min_momentum and 
            momentum > momentum_prev and
            positive_count >= 3):  # Al menos 3 de 5 velas
            long_score += 1
        
        # 6. Precio cerca de EMA_50 (rebote) (peso: 1)
        if abs(price - ema_50) / ema_50 < 0.005:  # Dentro del 0.5%
            long_score += 1
        
        # === CRITERIOS PARA SHORT ===
        
        # 1. Tendencia bajista (peso: 1)
        if price < ema_200 * 0.998:  # 0.2% por debajo
            short_score += 1
        
        # 2. RSI favorable (peso: 1)
        if 35 < rsi < 70 and rsi < rsi_prev:
            short_score += 1
        
        # 3. MACD cruce bajista REAL (peso: 1)
        if (macd_line < macd_signal and 
            macd_line_prev >= macd_signal_prev and
            (macd_signal - macd_line) > tolerance):
            short_score += 1
        
        # 4. Precio bajando (peso: 1)
        if price < price_prev:
            short_score += 1
        
        # 5. Momentum negativo Y consistente (peso: 1)
        if (not pd.isna(momentum) and 
            momentum < -min_momentum and 
            momentum < momentum_prev and
            negative_count >= 3):  # Al menos 3 de 5 velas
            short_score += 1
        
        # 6. Precio cerca de EMA_50 (rechazo) (peso: 1)
        if abs(price - ema_50) / ema_50 < 0.005:  # Dentro del 0.5%
            short_score += 1
        
        # REQUIERE puntuación mínima de 4/6 (67%)
        if long_score >= 4:
            return 'long'
        elif short_score >= 4:
            return 'short'
        
        return None

    @staticmethod
    def strategy_swing_trading_multi_indicator(df):
        """
        Estrategia de Swing Trading OPTIMIZADA.
        
        Mejoras:
        - Tendencia FUERTE requerida (sin tolerancia)
        - Pullback REAL confirmado en 5 velas
        - Requiere 3 confirmaciones (no 2)
        - MACD con cruces reales
        - Momentum consistente
        """
        required = ['close', 'ema_50', 'ema_200', 'rsi', 'macd_line', 'macd_signal', 'momentum']
        if not all(col in df.columns for col in required) or len(df) < 200:
            return None

        # Datos actuales
        price = df['close'].iloc[-1]
        price_prev = df['close'].iloc[-2]
        ema_50 = df['ema_50'].iloc[-1]
        ema_200 = df['ema_200'].iloc[-1]
        rsi = df['rsi'].iloc[-1]
        rsi_prev = df['rsi'].iloc[-2]
        macd_line = df['macd_line'].iloc[-1]
        macd_signal = df['macd_signal'].iloc[-1]
        macd_line_prev = df['macd_line'].iloc[-2]
        macd_signal_prev = df['macd_signal'].iloc[-2]
        momentum = df['momentum'].iloc[-1]
        momentum_prev = df['momentum'].iloc[-2]
        
        # Tendencia FUERTE (sin tolerancia)
        is_strong_uptrend = ema_50 > ema_200 * 1.003 and price > ema_50  # 0.3% mínimo
        is_strong_downtrend = ema_50 < ema_200 * 0.997 and price < ema_50
        
        # Tolerancia y momentum mínimo
        tolerance = abs(price * 0.00001)
        min_momentum = abs(price * 0.00005)

        # === LONG (Pullback en tendencia alcista) ===
        if is_strong_uptrend:
            # Pullback REAL: precio tocó EMA_50 en últimas 5 velas
            pullback_real = (df['low'].iloc[-5:] <= ema_50 * 1.002).any()
            
            if pullback_real:
                # CONFIRMACIÓN 1: MACD cruce alcista REAL
                macd_cross_up = (
                    macd_line > macd_signal and 
                    macd_line_prev <= macd_signal_prev and
                    (macd_line - macd_signal) > tolerance
                )
                
                # CONFIRMACIÓN 2: RSI saliendo de zona baja
                rsi_ok = 35 <= rsi <= 60 and rsi > rsi_prev
                
                # CONFIRMACIÓN 3: Precio rebotando
                price_bouncing = price > ema_50 and price > price_prev
                
                # CONFIRMACIÓN 4: Momentum positivo
                momentum_ok = (not pd.isna(momentum) and 
                              momentum > min_momentum and 
                              momentum > momentum_prev)
                
                # REQUIERE 3 de 4
                confirmations = [macd_cross_up, rsi_ok, price_bouncing, momentum_ok]
                if sum(confirmations) >= 3:
                    return 'long'

        # === SHORT (Pullback en tendencia bajista) ===
        if is_strong_downtrend:
            # Pullback REAL: precio tocó EMA_50 en últimas 5 velas
            pullback_real = (df['high'].iloc[-5:] >= ema_50 * 0.998).any()
            
            if pullback_real:
                # CONFIRMACIÓN 1: MACD cruce bajista REAL
                macd_cross_down = (
                    macd_line < macd_signal and 
                    macd_line_prev >= macd_signal_prev and
                    (macd_signal - macd_line) > tolerance
                )
                
                # CONFIRMACIÓN 2: RSI saliendo de zona alta
                rsi_ok = 40 <= rsi <= 65 and rsi < rsi_prev
                
                # CONFIRMACIÓN 3: Precio rechazando
                price_rejecting = price < ema_50 and price < price_prev
                
                # CONFIRMACIÓN 4: Momentum negativo
                momentum_ok = (not pd.isna(momentum) and 
                              momentum < -min_momentum and 
                              momentum < momentum_prev)
                
                # REQUIERE 3 de 4
                confirmations = [macd_cross_down, rsi_ok, price_rejecting, momentum_ok]
                if sum(confirmations) >= 3:
                    return 'short'

        return None

    @staticmethod
    def strategy_candle_pattern_reversal(df):
        """
        Estrategia de Reversión por Patrones de Velas OPTIMIZADA.
        
        Mejoras:
        - Score requerido aumentado a 4 (antes 3)
        - Pesos de patrones ajustados
        - Confirmación con momentum real
        - Filtro de tendencia más estricto
        """
        required = ['open', 'high', 'low', 'close', 'rsi', 'ema_200', 'momentum']
        if not all(col in df.columns for col in required) or len(df) < 20:
            return None
        
        # Datos actuales
        price = df['close'].iloc[-1]
        ema_200 = df['ema_200'].iloc[-1]
        rsi = df['rsi'].iloc[-1]
        rsi_prev = df['rsi'].iloc[-2]
        momentum = df['momentum'].iloc[-1]
        momentum_prev = df['momentum'].iloc[-2]
        
        # Momentum mínimo
        min_momentum = abs(price * 0.00005)
        
        # Tendencia
        is_uptrend_or_neutral = price > ema_200 * 0.998
        is_downtrend_or_neutral = price < ema_200 * 1.002
        
        # Detectar patrones
        candles_list = df.to_dict('records')
        current_index = len(candles_list) - 1
        
        try:
            signals = CandlePatterns.detect_all_patterns(candles_list, current_index)
        except:
            return None
        
        # === Scoring OPTIMIZADO ===
        
        # Patrones alcistas con PESOS AUMENTADOS
        bullish_patterns = {
            'hammer': 2.0,  # Aumentado de 1.5
            'bullish_engulfing': 2.0,
            'morning_star': 2.5,  # Aumentado de 2.0
            'three_white_soldiers': 2.5,
            'piercing_line': 1.5
        }
        
        # Patrones bajistas con PESOS AUMENTADOS
        bearish_patterns = {
            'shooting_star': 2.0,
            'bearish_engulfing': 2.0,
            'evening_star': 2.5,
            'three_black_crows': 2.5,
            'dark_cloud_cover': 1.5
        }
        
        # Calcular scores
        long_score = sum(bullish_patterns.get(p, 0) for p in signals.get('long', []))
        short_score = sum(bearish_patterns.get(p, 0) for p in signals.get('short', []))
        
        # === LONG ===
        if is_uptrend_or_neutral and long_score > 0:
            # Confirmaciones adicionales
            rsi_ok = rsi < 55 and rsi > rsi_prev
            momentum_ok = (not pd.isna(momentum) and 
                          momentum > min_momentum and 
                          momentum > momentum_prev)
            price_rising = price > df['close'].iloc[-2]
            
            # Bonus por confirmaciones
            if rsi_ok:
                long_score += 0.5
            if momentum_ok:
                long_score += 0.5
            if price_rising:
                long_score += 0.5
            
            # Score mínimo AUMENTADO a 4
            if long_score >= 4:
                return 'long'
        
        # === SHORT ===
        if is_downtrend_or_neutral and short_score > 0:
            # Confirmaciones adicionales
            rsi_ok = rsi > 45 and rsi < rsi_prev
            momentum_ok = (not pd.isna(momentum) and 
                          momentum < -min_momentum and 
                          momentum < momentum_prev)
            price_falling = price < df['close'].iloc[-2]
            
            # Bonus por confirmaciones
            if rsi_ok:
                short_score += 0.5
            if momentum_ok:
                short_score += 0.5
            if price_falling:
                short_score += 0.5
            
            # Score mínimo AUMENTADO a 4
            if short_score >= 4:
                return 'short'
        
        return None

    @staticmethod
    def strategy_momentum_rsi_macd(df):
        """
        Estrategia de Momentum ESTRICTA que combina RSI, MACD y tendencia.
        
        Lógica CORREGIDA:
        - Requiere TODAS las condiciones (no 2 de 3)
        - MACD: Solo cruces REALES con separación mínima
        - Momentum: Debe ser consistente en múltiples velas
        - Evita señales falsas en mercado lateral
        """
        required = ['close', 'ema_200', 'rsi', 'macd_line', 'macd_signal', 'momentum']
        if not all(col in df.columns for col in required) or len(df) < 10:
            return None

        # Verificar que tengamos suficientes velas para análisis
        if len(df) < 10:
            return None

        # --- 1. Filtro de Tendencia ESTRICTO ---
        price = df['close'].iloc[-1]
        ema_200 = df['ema_200'].iloc[-1]
        
        # Debe estar claramente por encima/debajo de EMA_200
        is_uptrend = price > ema_200 * 1.002  # 0.2% por encima
        is_downtrend = price < ema_200 * 0.998  # 0.2% por debajo
        
        # Si estamos en zona neutral (cerca de EMA_200), NO operar
        if not is_uptrend and not is_downtrend:
            return None

        # --- 2. Indicadores actuales y previos ---
        rsi = df['rsi'].iloc[-1]
        rsi_prev = df['rsi'].iloc[-2]
        macd_line = df['macd_line'].iloc[-1]
        macd_signal = df['macd_signal'].iloc[-1]
        macd_line_prev = df['macd_line'].iloc[-2]
        macd_signal_prev = df['macd_signal'].iloc[-2]
        momentum = df['momentum'].iloc[-1]
        momentum_prev = df['momentum'].iloc[-2]
        
        # --- 3. Verificar Momentum CONSISTENTE en últimas 5 velas ---
        recent_momentum = df['momentum'].iloc[-5:].values
        positive_momentum_count = sum(m > 0 for m in recent_momentum if not pd.isna(m))
        negative_momentum_count = sum(m < 0 for m in recent_momentum if not pd.isna(m))
        
        # Momentum debe ser consistente (al menos 70% de velas)
        has_bullish_momentum = positive_momentum_count >= 4  # 4 de 5 velas
        has_bearish_momentum = negative_momentum_count >= 4

        # --- 4. LÓGICA ESTRICTA PARA LONG ---
        if is_uptrend:
            # Tolerancia para detectar cruces reales
            tolerance = abs(price * 0.00001)  # 0.001% del precio
            
            # MACD: Cruce alcista REAL (debe haber separación clara)
            macd_cross_up = (
                macd_line > macd_signal and 
                macd_line_prev <= macd_signal_prev and
                (macd_line - macd_signal) > tolerance
            )
            
            # RSI: Zona favorable y mejorando
            rsi_favorable = 35 <= rsi <= 65 and rsi > rsi_prev
            
            # Momentum: Positivo Y mejorando
            min_momentum = abs(price * 0.00005)
            momentum_positive = not pd.isna(momentum) and momentum > min_momentum
            momentum_improving = momentum > momentum_prev if not pd.isna(momentum_prev) else False
            
            # Precio: Debe estar subiendo
            price_rising = price > df['close'].iloc[-2]
            
            # REQUIERE TODAS LAS CONDICIONES
            if (macd_cross_up and 
                rsi_favorable and 
                momentum_positive and 
                momentum_improving and
                has_bullish_momentum and
                price_rising):
                return 'long'

        # --- 5. LÓGICA ESTRICTA PARA SHORT ---
        if is_downtrend:
            tolerance = abs(price * 0.00001)
            
            # MACD: Cruce bajista REAL (debe haber separación clara)
            macd_cross_down = (
                macd_line < macd_signal and 
                macd_line_prev >= macd_signal_prev and
                (macd_signal - macd_line) > tolerance
            )
            
            # RSI: Zona favorable y empeorando
            rsi_favorable = 35 <= rsi <= 65 and rsi < rsi_prev
            
            # Momentum: Negativo Y empeorando
            min_momentum = abs(price * 0.00005)
            momentum_negative = not pd.isna(momentum) and momentum < -min_momentum
            momentum_worsening = momentum < momentum_prev if not pd.isna(momentum_prev) else False
            
            # Precio: Debe estar bajando
            price_falling = price < df['close'].iloc[-2]
            
            # REQUIERE TODAS LAS CONDICIONES
            if (macd_cross_down and 
                rsi_favorable and 
                momentum_negative and 
                momentum_worsening and
                has_bearish_momentum and
                price_falling):
                return 'short'

        return None

    @staticmethod
    def strategy_chart_pattern_breakout(df, lookback=60):
        """
        Estrategia de Patrones Gráficos OPTIMIZADA (Rompimientos).
        
        Mejoras:
        - Tolerancia reducida de 4% a 1%
        - Confirmación con momentum real
        - Reversión verificada en 3 velas
        - RSI más estricto (<40 para LONG, >60 para SHORT)
        - Requiere 3 de 4 confirmaciones
        """
        required = ['high', 'low', 'close', 'atr', 'rsi', 'momentum']
        if not all(col in df.columns for col in required) or len(df) < lookback:
            return None

        df_lookback = df.iloc[-lookback:]
        
        # Prominencia más estricta
        prominence = df_lookback['atr'].iloc[-1] * 1.5  # Aumentado de 1.2 a 1.5
        
        # Detectar picos y valles
        peaks, _ = find_peaks(df_lookback['high'], prominence=prominence)
        valleys, _ = find_peaks(-df_lookback['low'], prominence=prominence)
        
        # Datos actuales
        current_close = df_lookback['close'].iloc[-1]
        prev_close = df_lookback['close'].iloc[-2]
        rsi = df['rsi'].iloc[-1]
        rsi_prev = df['rsi'].iloc[-2]
        momentum = df['momentum'].iloc[-1]
        momentum_prev = df['momentum'].iloc[-2]
        
        # Momentum mínimo requerido
        min_momentum = abs(current_close * 0.00005)
        
        # Verificar reversión con 3 velas
        if len(df) >= 3:
            close_3_ago = df['close'].iloc[-3]
            close_2_ago = df['close'].iloc[-2]
            
            bullish_reversal = (
                close_3_ago > close_2_ago > prev_close and
                current_close > prev_close
            )
            
            bearish_reversal = (
                close_3_ago < close_2_ago < prev_close and
                current_close < prev_close
            )
        else:
            bullish_reversal = current_close > prev_close
            bearish_reversal = current_close < prev_close

        # === SHORT: Doble techo con tolerancia ESTRICTA ===
        if len(peaks) >= 2:
            p1_idx, p2_idx = peaks[-2], peaks[-1]
            p1_high = df_lookback['high'].iloc[p1_idx]
            p2_high = df_lookback['high'].iloc[p2_idx]

            # Tolerancia REDUCIDA de 4% a 1%
            if abs(p1_high - p2_high) / p1_high < 0.01:  # 1% tolerancia
                neckline = df_lookback['low'].iloc[p1_idx:p2_idx].min()
                
                # Confirmación de rompimiento con tolerancia estricta
                breakout_confirmed = (
                    current_close < neckline * 0.998 and 
                    prev_close >= neckline
                )
                
                if breakout_confirmed:
                    # CONFIRMACIÓN 1: RSI en zona alta (saliendo de sobrecompra)
                    rsi_ok = rsi > 60 and rsi < rsi_prev
                    
                    # CONFIRMACIÓN 2: Momentum negativo
                    momentum_ok = (not pd.isna(momentum) and 
                                  momentum < -min_momentum and 
                                  momentum < momentum_prev)
                    
                    # CONFIRMACIÓN 3: Reversión bajista confirmada
                    reversal_ok = bearish_reversal
                    
                    # CONFIRMACIÓN 4: Precio cayendo
                    price_falling = current_close < prev_close
                    
                    # REQUIERE 3 de 4 confirmaciones
                    confirmations = [rsi_ok, momentum_ok, reversal_ok, price_falling]
                    if sum(confirmations) >= 3:
                        return 'short'

        # === LONG: Doble suelo con tolerancia ESTRICTA ===
        if len(valleys) >= 2:
            v1_idx, v2_idx = valleys[-2], valleys[-1]
            v1_low = df_lookback['low'].iloc[v1_idx]
            v2_low = df_lookback['low'].iloc[v2_idx]

            # Tolerancia REDUCIDA de 4% a 1%
            if abs(v1_low - v2_low) / v1_low < 0.01:  # 1% tolerancia
                neckline = df_lookback['high'].iloc[v1_idx:v2_idx].max()
                
                # Confirmación de rompimiento con tolerancia estricta
                breakout_confirmed = (
                    current_close > neckline * 1.002 and 
                    prev_close <= neckline
                )
                
                if breakout_confirmed:
                    # CONFIRMACIÓN 1: RSI en zona baja (saliendo de sobreventa)
                    rsi_ok = rsi < 40 and rsi > rsi_prev
                    
                    # CONFIRMACIÓN 2: Momentum positivo
                    momentum_ok = (not pd.isna(momentum) and 
                                  momentum > min_momentum and 
                                  momentum > momentum_prev)
                    
                    # CONFIRMACIÓN 3: Reversión alcista confirmada
                    reversal_ok = bullish_reversal
                    
                    # CONFIRMACIÓN 4: Precio subiendo
                    price_rising = current_close > prev_close
                    
                    # REQUIERE 3 de 4 confirmaciones
                    confirmations = [rsi_ok, momentum_ok, reversal_ok, price_rising]
                    if sum(confirmations) >= 3:
                        return 'long'

        return None