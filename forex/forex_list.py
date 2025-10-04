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
    def strategy_price_action_sr(df, lookback=25):
        """
        Estrategia Price Action OPTIMIZADA para M1.
        Focus en S/R dinámicos con confirmación rápida y filtros M1.
        """
        # --- VERIFICACIONES INICIALES M1 ---
        required = ['low', 'high', 'close', 'ema_50', 'rsi', 'atr']
        if not all(col in df.columns for col in required) or len(df) < lookback:
            return None

        # --- FILTRO DE VOLATILIDAD M1 ---
        current_atr = df['atr'].iloc[-1]
        avg_atr = df['atr'].rolling(20).mean().iloc[-1]
        
        # Evitar periodos de volatilidad extrema
        if current_atr > avg_atr * 2.5:
            return None

        # --- 1. IDENTIFICACIÓN S/R DINÁMICA M1 ---
        recent_data = df.iloc[-lookback:]
        
        # Soportes: Mínimos locales últimos 25 velas
        support_levels = []
        for i in range(2, len(recent_data)-2):
            if (recent_data['low'].iloc[i] < recent_data['low'].iloc[i-1] and
                recent_data['low'].iloc[i] < recent_data['low'].iloc[i-2] and
                recent_data['low'].iloc[i] < recent_data['low'].iloc[i+1] and
                recent_data['low'].iloc[i] < recent_data['low'].iloc[i+2]):
                support_levels.append(recent_data['low'].iloc[i])

        # Resistencias: Máximos locales últimos 25 velas
        resistance_levels = []
        for i in range(2, len(recent_data)-2):
            if (recent_data['high'].iloc[i] > recent_data['high'].iloc[i-1] and
                recent_data['high'].iloc[i] > recent_data['high'].iloc[i-2] and
                recent_data['high'].iloc[i] > recent_data['high'].iloc[i+1] and
                recent_data['high'].iloc[i] > recent_data['high'].iloc[i+2]):
                resistance_levels.append(recent_data['high'].iloc[i])

        if not support_levels or not resistance_levels:
            return None

        # Tomar los 2 niveles más recientes de cada uno
        current_support = sorted(support_levels)[-2] if len(support_levels) >= 2 else support_levels[-1]
        current_resistance = sorted(resistance_levels)[-2] if len(resistance_levels) >= 2 else resistance_levels[-1]

        # --- 2. FILTRO TENDENCIA M1 ---
        price = df['close'].iloc[-1]
        ema_20 = df['ema_20'].iloc[-1] if 'ema_20' in df.columns else df['ema_50'].iloc[-1]
        ema_50 = df['ema_50'].iloc[-1]
        
        # Tendencia más reactiva para M1
        is_uptrend = price > ema_20 and ema_20 > ema_50
        is_downtrend = price < ema_20 and ema_20 < ema_50

        # --- 3. DETECCIÓN PATRONES VELAS M1 ---
        candle_data = df.to_dict('records')
        current_index = len(candle_data) - 1
        
        # Usar solo patrones de alta probabilidad para M1
        signals = CandlePatterns.detect_all_patterns(candle_data, current_index)
        
        # Patrones M1 específicos
        m1_bullish_patterns = ['hammer', 'bullish_engulfing', 'piercing_line', 'morning_star']
        m1_bearish_patterns = ['shooting_star', 'bearish_engulfing', 'dark_cloud_cover', 'evening_star']
        
        has_bullish_pattern = any(p in signals['long'] for p in m1_bullish_patterns)
        has_bearish_pattern = any(p in signals['short'] for p in m1_bearish_patterns)

        # --- 4. TOLERANCIA DINÁMICA M1 ---
        tolerance = current_atr * 0.8  # 80% del ATR actual

        # --- 5. LÓGICA MEJORADA M1 ---
        current_low = df['low'].iloc[-1]
        current_high = df['high'].iloc[-1]
        current_close = df['close'].iloc[-1]
        rsi = df['rsi'].iloc[-1]

        # SEÑAL LONG: Rebote en soporte + tendencia alcista
        if (is_uptrend and 
            abs(current_low - current_support) <= tolerance and
            has_bullish_pattern and
            rsi < 55 and  # Más flexible para M1
            current_close > df['open'].iloc[-1]):  # Vela alcista de confirmación
            
            # Confirmación adicional: precio sobre apertura
            return 'long'

        # SEÑAL SHORT: Rebote en resistencia + tendencia bajista  
        if (is_downtrend and
            abs(current_high - current_resistance) <= tolerance and
            has_bearish_pattern and
            rsi > 45 and  # Más flexible para M1
            current_close < df['open'].iloc[-1]):  # Vela bajista de confirmación
            
            return 'short'

        return None

    @staticmethod
    def strategy_ma_crossover(df):
        """
        Estrategia MA Crossover OPTIMIZADA para M1.
        Combina múltiples EMA con filtros de tendencia, volumen y volatilidad para reducir señales falsas.
        """
        # --- VERIFICACIONES INICIALES M1 ---
        required = ['close', 'ema_8', 'ema_21', 'ema_50', 'atr']
        if not all(col in df.columns for col in required) or len(df) < 50:
            return None

        # --- FILTRO DE VOLATILIDAD M1 ---
        current_atr = df['atr'].iloc[-1]
        avg_atr = df['atr'].rolling(25).mean().iloc[-1]
        
        # Evitar condiciones de mercado desfavorables para MA crossover
        if (current_atr < avg_atr * 0.3 or  # Volatilidad muy baja (mucho ruido)
            current_atr > avg_atr * 2.5):   # Volatilidad muy alta (whiplash)
            return None

        # --- 1. CONFIGURACIÓN EMA RÁPIDA M1 ---
        # EMA más rápidas y sensibles para M1
        ema_fast = df['ema_8'].iloc[-1]     # Muy rápida (8 períodos)
        ema_medium = df['ema_21'].iloc[-1]  # Media (21 períodos)
        ema_slow = df['ema_50'].iloc[-1]    # Lenta (50 períodos)
        
        # Valores anteriores para detectar cruces
        ema_fast_prev = df['ema_8'].iloc[-2]
        ema_medium_prev = df['ema_21'].iloc[-2]
        ema_slow_prev = df['ema_50'].iloc[-2]
        
        current_price = df['close'].iloc[-1]
        previous_price = df['close'].iloc[-2]

        # --- 2. DETECCIÓN DE CRUCES MÚLTIPLES M1 ---
        
        # CRUCE PRINCIPAL: Fast sobre Medium
        fast_medium_cross_up = ema_fast > ema_medium and ema_fast_prev <= ema_medium_prev
        fast_medium_cross_down = ema_fast < ema_medium and ema_fast_prev >= ema_medium_prev
        
        # CRUCE SECUNDARIO: Medium sobre Slow  
        medium_slow_cross_up = ema_medium > ema_slow and ema_medium_prev <= ema_slow_prev
        medium_slow_cross_down = ema_medium < ema_slow and ema_medium_prev >= ema_slow_prev
        
        # ALINEACIÓN DE TENDENCIA
        bullish_alignment = ema_fast > ema_medium > ema_slow
        bearish_alignment = ema_fast < ema_medium < ema_slow

        # --- 3. FILTRO DE TENDENCIA PRINCIPAL M1 ---
        # Usar EMA 50 como filtro de tendencia principal
        price_above_slow = current_price > ema_slow
        price_below_slow = current_price < ema_slow
        
        # Fuerza de la tendencia
        trend_strength = abs(ema_fast - ema_slow) / current_price
        strong_trend = trend_strength > (current_atr * 0.8 / current_price)

        # --- 4. CONFIRMACIÓN DE MOMENTUM M1 ---
        momentum_bullish = False
        momentum_bearish = False
        
        if 'rsi' in df.columns:
            rsi = df['rsi'].iloc[-1]
            rsi_prev = df['rsi'].iloc[-2]
            
            # Momentum alcista: RSI subiendo y no sobrecomprado
            momentum_bullish = (rsi > 40 and rsi < 70 and 
                            rsi > rsi_prev and 
                            current_price > previous_price)
            
            # Momentum bajista: RSI bajando y no sobrevendido
            momentum_bearish = (rsi > 30 and rsi < 60 and 
                            rsi < rsi_prev and 
                            current_price < previous_price)
        else:
            # Fallback: usar precio como momentum
            momentum_bullish = current_price > previous_price
            momentum_bearish = current_price < previous_price

        # --- 5. CONFIRMACIÓN DE VOLUMEN M1 ---
        volume_confirmation = True
        if 'tick_volume' in df.columns and len(df) > 10:
            current_volume = df['tick_volume'].iloc[-1]
            avg_volume = df['tick_volume'].rolling(10).mean().iloc[-1]
            volume_confirmation = current_volume > avg_volume * 0.8

        # --- 6. ANÁLISIS DE ÁNGULO Y SEPARACIÓN M1 ---
        # Calcular la separación entre EMAs (evitar cruces muy cercanos)
        fast_medium_separation = abs(ema_fast - ema_medium) / current_price
        medium_slow_separation = abs(ema_medium - ema_slow) / current_price
        
        min_separation = current_atr * 0.0001  # Separación mínima requerida
        
        separation_ok = (fast_medium_separation > min_separation and 
                        medium_slow_separation > min_separation)

        # --- 7. SISTEMA DE PUNTUACIÓN M1 ---
        
        # CONDICIONES LONG
        long_conditions = [
            fast_medium_cross_up,                    # 3 pts: Cruce principal
            medium_slow_cross_up or bullish_alignment, # 2 pts: Alineación o cruce secundario
            price_above_slow,                        # 2 pts: Precio sobre EMA lenta
            momentum_bullish,                        # 1 pt:  Momentum confirmado
            volume_confirmation,                     # 1 pt:  Volumen adecuado
            separation_ok,                           # 1 pt:  Separación suficiente
            strong_trend,                            # 1 pt:  Tendencia fuerte
        ]
        
        long_score = sum([3 if i == 0 else 2 if i in [1, 2] else 1 for i, condition in enumerate(long_conditions) if condition])

        # CONDICIONES SHORT
        short_conditions = [
            fast_medium_cross_down,                  # 3 pts: Cruce principal
            medium_slow_cross_down or bearish_alignment, # 2 pts: Alineación o cruce secundario
            price_below_slow,                        # 2 pts: Precio bajo EMA lenta
            momentum_bearish,                        # 1 pt:  Momentum confirmado
            volume_confirmation,                     # 1 pt:  Volumen adecuado
            separation_ok,                           # 1 pt:  Separación suficiente
            strong_trend,                            # 1 pt:  Tendencia fuerte
        ]
        
        short_score = sum([3 if i == 0 else 2 if i in [1, 2] else 1 for i, condition in enumerate(short_conditions) if condition])

        # --- 8. LÓGICA FINAL DE SEÑALES M1 ---
        min_score = 6  # Puntuación mínima para señal válida

        # SEÑAL LONG: Puntuación alta y mejor que short
        if (long_score >= min_score and 
            long_score > short_score and
            # Filtro adicional: evitar cruces contra la tendencia principal
            (bullish_alignment or medium_slow_cross_up)):
            
            # Confirmación final: patrón de vela alcista
            candle_data = df.to_dict('records')
            current_index = len(candle_data) - 1
            candle_signals = CandlePatterns.detect_all_patterns(candle_data, current_index)
            
            bullish_candle_confirmation = any(p in candle_signals['long'] for p in ['bullish_engulfing', 'hammer', 'marubozu'])
            
            if bullish_candle_confirmation or current_price > df['open'].iloc[-1]:
                return 'long'

        # SEÑAL SHORT: Puntuación alta y mejor que long
        if (short_score >= min_score and 
            short_score > long_score and
            # Filtro adicional: evitar cruces contra la tendencia principal
            (bearish_alignment or medium_slow_cross_down)):
            
            # Confirmación final: patrón de vela bajista
            candle_data = df.to_dict('records')
            current_index = len(candle_data) - 1
            candle_signals = CandlePatterns.detect_all_patterns(candle_data, current_index)
            
            bearish_candle_confirmation = any(p in candle_signals['short'] for p in ['bearish_engulfing', 'shooting_star', 'marubozu'])
            
            if bearish_candle_confirmation or current_price < df['open'].iloc[-1]:
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
        """
        Estrategia Ichimoku OPTIMIZADA para M1.
        Versión rápida con períodos adaptados para scalping y señales más reactivas.
        """
        # --- VERIFICACIONES INICIALES M1 ---
        required = ['close', 'tenkan_sen', 'kijun_sen', 'senkou_span_a', 'senkou_span_b', 'chikou_span']
        if not all(col in df.columns for col in required) or len(df) < 30:
            return None

        # --- CONFIGURACIÓN ICHIMOKU RÁPIDO M1 ---
        # Para M1 usamos períodos más cortos del Ichimoku estándar
        current_price = df['close'].iloc[-1]
        tenkan = df['tenkan_sen'].iloc[-1]      # Línea de conversión (9)
        kijun = df['kijun_sen'].iloc[-1]        # Línea base (26) 
        senkou_a = df['senkou_span_a'].iloc[-1] # Leading Span A
        senkou_b = df['senkou_span_b'].iloc[-1] # Leading Span B
        chikou = df['chikou_span'].iloc[-1]     # Línea retrasada

        # Valores anteriores para detectar cruces
        tenkan_prev = df['tenkan_sen'].iloc[-2]
        kijun_prev = df['kijun_sen'].iloc[-2]
        price_prev = df['close'].iloc[-2]

        # --- 1. ANÁLISIS DE LA NUBE (KUMO) MEJORADO M1 ---
        kumo_top = max(senkou_a, senkou_b)
        kumo_bottom = min(senkou_a, senkou_b)
        kumo_thickness = abs(senkou_a - senkou_b)
        
        # Posición relativa respecto a la nube
        is_above_kumo = current_price > kumo_top
        is_below_kumo = current_price < kumo_bottom
        is_inside_kumo = kumo_bottom <= current_price <= kumo_top
        
        # Fuerza de la nube
        is_kumo_bullish = senkou_a > senkou_b  # Nube alcista
        is_kumo_bearish = senkou_a < senkou_b  # Nube bajista
        is_kumo_thick = kumo_thickness > (current_price * 0.0005)  # Nube significativa

        # --- 2. SEÑALES DE CRUCE RÁPIDAS M1 ---
        # TK Cross (Tenkan/Kijun) - Señal principal
        tk_cross_up = tenkan > kijun and tenkan_prev <= kijun_prev
        tk_cross_down = tenkan < kijun and tenkan_prev >= kijun_prev
        
        # Price/Kijun Cross - Señal secundaria
        pk_cross_up = current_price > kijun and price_prev <= kijun_prev
        pk_cross_down = current_price < kijun and price_prev >= kijun_prev

        # --- 3. ANÁLISIS CHIKOU SPAN (LÍNEA RETRASADA) M1 ---
        # Chikou span debería estar por encima/del precio de hace 26 periodos
        chikou_position = "neutral"
        if len(df) > 26:
            price_26_periods_ago = df['close'].iloc[-26]
            if chikou > price_26_periods_ago:
                chikou_position = "bullish"
            elif chikou < price_26_periods_ago:
                chikou_position = "bearish"

        # --- 4. SEÑALES KUMO BREAKOUT M1 ---
        # Rompimiento de nube reciente
        kumo_breakout_up = (current_price > kumo_top and 
                        df['high'].iloc[-2] <= kumo_top and
                        is_kumo_thick)
        
        kumo_breakout_down = (current_price < kumo_bottom and 
                            df['low'].iloc[-2] >= kumo_bottom and
                            is_kumo_thick)

        # --- 5. CONFIRMACIÓN CON INDICADORES ADICIONALES M1 ---
        # RSI para filtrar señales extremas
        rsi_filter = True
        if 'rsi' in df.columns:
            rsi = df['rsi'].iloc[-1]
            rsi_filter = 30 < rsi < 70  # Evitar sobrecompra/venta extrema

        # Volumen para confirmación (si disponible)
        volume_confirmation = True
        if 'tick_volume' in df.columns and len(df) > 10:
            current_volume = df['tick_volume'].iloc[-1]
            avg_volume = df['tick_volume'].iloc[-10:].mean()
            volume_confirmation = current_volume > avg_volume * 0.7

        # --- 6. SISTEMA DE PUNTUACIÓN ICHIMOKU M1 ---
        
        # CONDICIONES LONG
        long_conditions = [
            is_above_kumo or kumo_breakout_up,          # 2 pts: Precio sobre nube
            tk_cross_up or pk_cross_up,                 # 2 pts: Cruce alcista
            is_kumo_bullish,                            # 1 pt:  Nube alcista
            chikou_position == "bullish",               # 1 pt:  Chikou alcista
            rsi_filter and volume_confirmation,         # 1 pt:  Confirmación adicional
        ]
        
        long_score = sum([2 if i in [0, 1] else 1 for i, condition in enumerate(long_conditions) if condition])

        # CONDICIONES SHORT
        short_conditions = [
            is_below_kumo or kumo_breakout_down,        # 2 pts: Precio bajo nube
            tk_cross_down or pk_cross_down,             # 2 pts: Cruce bajista
            is_kumo_bearish,                            # 1 pt:  Nube bajista
            chikou_position == "bearish",               # 1 pt:  Chikou bajista
            rsi_filter and volume_confirmation,         # 1 pt:  Confirmación adicional
        ]
        
        short_score = sum([2 if i in [0, 1] else 1 for i, condition in enumerate(short_conditions) if condition])

        # --- 7. LÓGICA DE SEÑALES MEJORADA M1 ---
        min_score = 4  # Puntuación mínima para señal válida

        # SEÑAL LONG FUERTE
        if (long_score >= min_score and 
            long_score > short_score and
            # Filtros adicionales para calidad de señal
            not is_inside_kumo and  # Evitar señales dentro de la nube
            current_price > tenkan):  # Precio sobre Tenkan
            return 'long'

        # SEÑAL SHORT FUERTE
        if (short_score >= min_score and 
            short_score > long_score and
            # Filtros adicionales para calidad de señal
            not is_inside_kumo and  # Evitar señales dentro de la nube
            current_price < tenkan):  # Precio bajo Tenkan
            return 'short'

        # --- 8. SEÑALES DE KUMO TWIST (CAMBIO DE NUBE) M1 ---
        # Señal adicional: cambio de color de la nube
        if len(df) > 2:
            senkou_a_prev = df['senkou_span_a'].iloc[-2]
            senkou_b_prev = df['senkou_span_b'].iloc[-2]
            
            kumo_twist_bullish = (senkou_a > senkou_b and 
                                senkou_a_prev <= senkou_b_prev and
                                current_price > kumo_top)
            
            kumo_twist_bearish = (senkou_a < senkou_b and 
                                senkou_a_prev >= senkou_b_prev and
                                current_price < kumo_bottom)
            
            if kumo_twist_bullish and long_score >= 3:
                return 'long'
            if kumo_twist_bearish and short_score >= 3:
                return 'short'

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
        Estrategia de Scalping OPTIMIZADA para M1.
        Combina StochRSI rápido con EMA, volumen y filtros S/R básicos.
        """
        # --- VERIFICACIONES INICIALES M1 ---
        required = ['close', 'stochrsi_k', 'stochrsi_d', 'ema_9', 'ema_20', 'atr']
        if not all(col in df.columns for col in required) or len(df) < 15:
            return None

        # --- FILTRO DE VOLATILIDAD M1 ---
        current_atr = df['atr'].iloc[-1]
        avg_atr = df['atr'].rolling(20).mean().iloc[-1]
        
        # Evitar volatilidad demasiado baja (mercado plano) o demasiado alta
        if current_atr < avg_atr * 0.3 or current_atr > avg_atr * 2.5:
            return None

        # --- 1. INDICADORES PRINCIPALES M1 ---
        close = df['close'].iloc[-1]
        stoch_k = df['stochrsi_k'].iloc[-1]
        stoch_d = df['stochrsi_d'].iloc[-1]
        stoch_k_prev = df['stochrsi_k'].iloc[-2]
        stoch_d_prev = df['stochrsi_d'].iloc[-2]
        
        # EMA más rápidas para M1
        ema_9 = df['ema_9'].iloc[-1]
        ema_20 = df['ema_20'].iloc[-1]
        ema_9_prev = df['ema_9'].iloc[-2]

        # --- 2. DETECCIÓN S/R RÁPIDA M1 ---
        # Soportes y resistencias de las últimas 15 velas
        recent_high = df['high'].iloc[-15:].max()
        recent_low = df['low'].iloc[-15:].min()
        recent_range = recent_high - recent_low
        
        # Niveles dinámicos basados en rango reciente
        dynamic_resistance = recent_high - (recent_range * 0.1)
        dynamic_support = recent_low + (recent_range * 0.1)

        # --- 3. ANÁLISIS DE MOMENTUM M1 ---
        # StochRSI mejorado para M1
        stoch_bullish_cross = stoch_k > stoch_d and stoch_k_prev <= stoch_d_prev
        stoch_bearish_cross = stoch_k < stoch_d and stoch_k_prev >= stoch_d_prev
        
        # Fuerza del momentum
        stoch_oversold = stoch_k < 25 and stoch_k > stoch_k_prev
        stoch_overbought = stoch_k > 75 and stoch_k < stoch_k_prev
        
        # --- 4. TENDENCIA MEJORADA M1 ---
        ema_bullish_alignment = ema_9 > ema_20 and close > ema_9
        ema_bearish_alignment = ema_9 < ema_20 and close < ema_9
        
        # Tendencia de corto plazo (últimas 5 velas)
        price_trend_bullish = df['close'].iloc[-1] > df['close'].iloc[-3]
        price_trend_bearish = df['close'].iloc[-1] < df['close'].iloc[-3]

        # --- 5. CONFIRMACIÓN DE VOLUMEN (si disponible) ---
        volume_confirmation = True
        if 'tick_volume' in df.columns and len(df) > 10:
            current_volume = df['tick_volume'].iloc[-1]
            avg_volume = df['tick_volume'].iloc[-10:].mean()
            volume_confirmation = current_volume > avg_volume * 0.8

        # --- 6. LÓGICA DE SEÑALES MEJORADA M1 ---

        # SEÑAL LONG FUERTE
        long_conditions = [
            ema_bullish_alignment,
            stoch_bullish_cross or stoch_oversold,
            price_trend_bullish,
            volume_confirmation,
            close > dynamic_support,  # No cerca de soporte (evitar breakdown)
            stoch_k < 80  # No sobrecomprado extremo
        ]
        
        # SEÑAL SHORT FUERTE
        short_conditions = [
            ema_bearish_alignment, 
            stoch_bearish_cross or stoch_overbought,
            price_trend_bearish,
            volume_confirmation,
            close < dynamic_resistance,  # No cerca de resistencia (evitar breakout)
            stoch_k > 20  # No sobrevendido extremo
        ]

        # --- 7. SISTEMA DE PUNTUACIÓN M1 ---
        long_score = sum(long_conditions)
        short_score = sum(short_conditions)
        
        # Umbral mínimo de confirmaciones
        min_confirmations = 4

        # --- 8. DECISIÓN FINAL CON FILTROS ADICIONALES ---
        
        # LONG: Alto score y mejor que short
        if (long_score >= min_confirmations and 
            long_score > short_score and
            # Filtro adicional: evitar señales en medio del rango sin dirección
            (abs(close - dynamic_support) < current_atr * 0.5 or 
            abs(close - dynamic_resistance) > current_atr * 1.0)):
            return 'long'
        
        # SHORT: Alto score y mejor que long  
        if (short_score >= min_confirmations and
            short_score > long_score and
            # Filtro adicional: evitar señales en medio del rango sin dirección
            (abs(close - dynamic_resistance) < current_atr * 0.5 or
            abs(close - dynamic_support) > current_atr * 1.0)):
            return 'short'

        return None

    @staticmethod
    def strategy_fibonacci_reversal(df, lookback=35):
        """
        Estrategia Fibonacci OPTIMIZADA para M1.
        Focus en retrocesos shallow y extensiones rápidas con confirmación de momentum.
        """
        # --- VERIFICACIONES INICIALES M1 ---
        required = ['high', 'low', 'close', 'atr', 'rsi']
        if not all(col in df.columns for col in required) or len(df) < lookback:
            return None

        # --- FILTRO DE VOLATILIDAD M1 ---
        current_atr = df['atr'].iloc[-1]
        avg_atr = df['atr'].rolling(25).mean().iloc[-1]
        
        # Fibonacci funciona mejor en volatilidad moderada
        if current_atr < avg_atr * 0.4 or current_atr > avg_atr * 2.0:
            return None

        # --- 1. IDENTIFICACIÓN DE SWING M1 MEJORADA ---
        recent_data = df.iloc[-lookback:]
        
        # Encontrar swing high y swing low más significativos
        swing_high = recent_data['high'].max()
        swing_low = recent_data['low'].min()
        
        # Verificar que el swing es reciente (últimas 15 velas)
        recent_swing_high = recent_data['high'].iloc[-15:].max()
        recent_swing_low = recent_data['low'].iloc[-15:].min()
        
        # Usar swings más recientes para M1
        swing_high = recent_swing_high
        swing_low = recent_swing_low
        
        price_range = swing_high - swing_low
        if price_range == 0:
            return None

        # --- 2. NIVELES FIBONACCI OPTIMIZADOS M1 ---
        # Niveles principales para M1 (más sensibles)
        fib_levels = {
            'shallow_38': swing_high - 0.382 * price_range,  # Más reactivo para M1
            'deep_50': swing_high - 0.50 * price_range,      # Nivel clave
            'deep_61': swing_high - 0.618 * price_range,     # Máximo retroceso aceptable
        }
        
        fib_extensions = {
            'ext_127': swing_low + 1.272 * price_range,      # Extensión alcista
            'ext_161': swing_low + 1.618 * price_range,      # Objetivo fuerte
        }

        current_price = df['close'].iloc[-1]
        current_low = df['low'].iloc[-1]
        current_high = df['high'].iloc[-1]

        # --- 3. TOLERANCIA DINÁMICA M1 ---
        tolerance = current_atr * 0.6  # Más ajustado para M1

        # --- 4. DETERMINAR DIRECCIÓN DEL MOVIMIENTO ---
        # Identificar si es movimiento alcista o bajista
        is_uptrend_move = swing_high > swing_low and (
            abs(swing_high - recent_data['high'].iloc[-1]) < 
            abs(swing_low - recent_data['low'].iloc[-1])
        )
        
        is_downtrend_move = swing_high > swing_low and not is_uptrend_move

        # --- 5. ANÁLISIS DE MOMENTUM PARA CONFIRMACIÓN ---
        rsi = df['rsi'].iloc[-1]
        rsi_prev = df['rsi'].iloc[-2]
        
        # Momentum alcista: RSI subiendo desde zonas bajas
        momentum_bullish = (rsi > 35 and rsi < 65 and 
                        rsi > rsi_prev and 
                        df['close'].iloc[-1] > df['close'].iloc[-2])
        
        # Momentum bajista: RSI bajando desde zonas altas
        momentum_bearish = (rsi > 35 and rsi < 65 and 
                        rsi < rsi_prev and 
                        df['close'].iloc[-1] < df['close'].iloc[-2])

        # --- 6. DETECCIÓN DE PATRONES DE VELAS EN NIVELES FIB ---
        candle_data = df.to_dict('records')
        current_index = len(candle_data) - 1
        signals = CandlePatterns.detect_all_patterns(candle_data, current_index)
        
        # Patrones específicos para Fibonacci en M1
        fib_bullish_patterns = ['hammer', 'bullish_engulfing', 'piercing_line', 'doji']
        fib_bearish_patterns = ['shooting_star', 'bearish_engulfing', 'dark_cloud_cover', 'doji']
        
        has_fib_bullish_pattern = any(p in signals['long'] for p in fib_bullish_patterns)
        has_fib_bearish_pattern = any(p in signals['short'] for p in fib_bearish_patterns)

        # --- 7. LÓGICA DE SEÑALES FIBONACCI M1 ---

        # SEÑAL LONG: Retroceso en tendencia alcista + rebote en Fib
        if is_uptrend_move:
            # Verificar niveles Fibonacci para long
            for level_name, level_price in fib_levels.items():
                distance_to_level = abs(current_low - level_price)
                
                # En nivel Fibonacci con patrón alcista
                if (distance_to_level <= tolerance and
                    has_fib_bullish_pattern and
                    momentum_bullish):
                    
                    # Confirmación adicional: precio debe mostrar reversión
                    if (df['close'].iloc[-1] > df['open'].iloc[-1] and  # Vela alcista
                        df['close'].iloc[-1] > df['low'].iloc[-1] + (current_atr * 0.3)):  # Fuerza
                        
                        # Filtro: evitar señales en el nivel 61.8% (muy profundo)
                        if level_name != 'deep_61' or rsi < 40:
                            return 'long'

            # SEÑAL LONG: Extensión Fibonacci alcista
            for ext_name, ext_price in fib_extensions.items():
                if (current_price >= ext_price and
                    abs(current_price - ext_price) <= tolerance and
                    has_fib_bearish_pattern and  # Posible reversión en extensión
                    rsi > 60):  # Sobrecompra en extensión
                    return 'short'  # Reversión desde extensión

        # SEÑAL SHORT: Retroceso en tendencia bajista + rebote en Fib
        if is_downtrend_move:
            # Para short, invertimos la lógica de niveles
            fib_levels_short = {
                'shallow_38': swing_low + 0.382 * price_range,
                'deep_50': swing_low + 0.50 * price_range,
                'deep_61': swing_low + 0.618 * price_range,
            }
            
            for level_name, level_price in fib_levels_short.items():
                distance_to_level = abs(current_high - level_price)
                
                # En nivel Fibonacci con patrón bajista
                if (distance_to_level <= tolerance and
                    has_fib_bearish_pattern and
                    momentum_bearish):
                    
                    # Confirmación adicional: precio debe mostrar reversión
                    if (df['close'].iloc[-1] < df['open'].iloc[-1] and  # Vela bajista
                        df['close'].iloc[-1] < df['high'].iloc[-1] - (current_atr * 0.3)):  # Fuerza
                        
                        # Filtro: evitar señales en el nivel 61.8% (muy profundo)
                        if level_name != 'deep_61' or rsi > 60:
                            return 'short'

            # SEÑAL SHORT: Extensión Fibonacci bajista
            fib_extensions_short = {
                'ext_127': swing_high - 1.272 * price_range,
                'ext_161': swing_high - 1.618 * price_range,
            }
            
            for ext_name, ext_price in fib_extensions_short.items():
                if (current_price <= ext_price and
                    abs(current_price - ext_price) <= tolerance and
                    has_fib_bullish_pattern and  # Posible reversión en extensión
                    rsi < 40):  # Sobreventa en extensión
                    return 'long'  # Reversión desde extensión

        return None

    @staticmethod
    def strategy_chart_pattern_breakout(df, lookback=30):
        """
        Estrategia de Breakout OPTIMIZADA para M1.
        Focus en rangos laterales y rompimientos con alta probabilidad.
        """
        # --- VERIFICACIONES INICIALES M1 ---
        required = ['high', 'low', 'close', 'atr', 'volume']
        if not all(col in df.columns for col in required) or len(df) < lookback:
            return None

        # --- FILTRO DE VOLUMEN Y VOLATILIDAD M1 ---
        current_atr = df['atr'].iloc[-1]
        avg_atr = df['atr'].rolling(20).mean().iloc[-1]
        current_volume = df['volume'].iloc[-1]
        avg_volume = df['volume'].rolling(20).mean().iloc[-1]

        # Evitar condiciones desfavorables
        if (current_atr < avg_atr * 0.4 or  # Volatilidad muy baja
            current_atr > avg_atr * 3.0 or  # Volatilidad muy alta
            current_volume < avg_volume * 0.7):  # Volumen insuficiente
            return None

        # --- 1. DETECCIÓN DE RANGO LATERAL M1 ---
        recent_data = df.iloc[-lookback:]
        
        # Calcular el rango de trading reciente
        recent_high = recent_data['high'].max()
        recent_low = recent_data['low'].min()
        recent_range = recent_high - recent_low
        current_close = df['close'].iloc[-1]
        
        # Verificar si estamos en un rango lateral (condición para breakout)
        range_threshold = current_atr * 0.3  # Umbral para considerar rango
        is_ranging = recent_range < (avg_atr * lookback * 0.15)  # Rango estrecho
        
        if not is_ranging:
            return None  # Solo operar en rangos identificados

        # --- 2. IDENTIFICACIÓN DE NIVELES CLAVE M1 ---
        # Encontrar niveles de soporte y resistencia del rango
        support_level = recent_low
        resistance_level = recent_high
        
        # Niveles de breakout (con buffer)
        breakout_bullish_level = resistance_level + (current_atr * 0.2)
        breakout_bearish_level = support_level - (current_atr * 0.2)

        # --- 3. ANÁLISIS DE CONSOLIDACIÓN M1 ---
        # Verificar consolidación previa al breakout
        consolidation_period = 0
        for i in range(2, min(10, len(recent_data))):
            if (abs(recent_data['high'].iloc[-i] - resistance_level) < range_threshold and
                abs(recent_data['low'].iloc[-i] - support_level) < range_threshold):
                consolidation_period += 1
        
        # Mínimo 3 velas de consolidación
        if consolidation_period < 3:
            return None

        # --- 4. DETECCIÓN DE ROMpIMIENTO M1 ---
        current_high = df['high'].iloc[-1]
        current_low = df['low'].iloc[-1]
        prev_high = df['high'].iloc[-2]
        prev_low = df['low'].iloc[-2]
        
        # ROMpIMIENTO ALCISTA
        bullish_breakout = (
            current_high > breakout_bullish_level and  # Rompe resistencia
            current_close > resistance_level and       # Cierra por encima
            prev_high <= resistance_level and          # Anterior no rompió
            current_volume > avg_volume * 1.2         # Volumen confirmatorio
        )
        
        # ROMpIMIENTO BAJISTA  
        bearish_breakout = (
            current_low < breakout_bearish_level and   # Rompe soporte
            current_close < support_level and          # Cierra por debajo
            prev_low >= support_level and              # Anterior no rompió
            current_volume > avg_volume * 1.2         # Volumen confirmatorio
        )

        # --- 5. CONFIRMACIÓN CON INDICADORES M1 ---
        # RSI para confirmar momentum (si disponible)
        rsi_confirmation = True
        if 'rsi' in df.columns:
            rsi = df['rsi'].iloc[-1]
            rsi_prev = df['rsi'].iloc[-2]
            
            rsi_bullish_confirmation = rsi > 45 and rsi > rsi_prev
            rsi_bearish_confirmation = rsi < 55 and rsi < rsi_prev
        else:
            rsi_bullish_confirmation = rsi_bearish_confirmation = True

        # --- 6. PATRONES DE VELAS DE CONFIRMACIÓN ---
        candle_data = df.to_dict('records')
        current_index = len(candle_data) - 1
        candle_signals = CandlePatterns.detect_all_patterns(candle_data, current_index)
        
        # Patrones que confirman breakout
        bullish_confirmation_patterns = ['bullish_engulfing', 'marubozu', 'three_white_soldiers']
        bearish_confirmation_patterns = ['bearish_engulfing', 'marubozu', 'three_black_crows']
        
        has_bullish_candle = any(p in candle_signals['long'] for p in bullish_confirmation_patterns)
        has_bearish_candle = any(p in candle_signals['short'] for p in bearish_confirmation_patterns)

        # --- 7. LÓGICA FINAL DE SEÑALES M1 ---

        # SEÑAL LONG: Breakout alcista confirmado
        if (bullish_breakout and 
            rsi_bullish_confirmation and
            (has_bullish_candle or current_volume > avg_volume * 1.5) and
            # Filtro adicional: el rompimiento debe ser significativo
            (current_high - resistance_level) > (current_atr * 0.15)):
            
            # Verificar que no es un falso breakout (wick largo)
            body_size = abs(current_close - df['open'].iloc[-1])
            upper_wick = current_high - max(current_close, df['open'].iloc[-1])
            
            if body_size > upper_wick * 1.5:  # Cuerpo mayor que wick superior
                return 'long'

        # SEÑAL SHORT: Breakout bajista confirmado
        if (bearish_breakout and
            rsi_bearish_confirmation and
            (has_bearish_candle or current_volume > avg_volume * 1.5) and
            # Filtro adicional: el rompimiento debe ser significativo
            (support_level - current_low) > (current_atr * 0.15)):
            
            # Verificar que no es un falso breakout (wick largo)
            body_size = abs(current_close - df['open'].iloc[-1])
            lower_wick = min(current_close, df['open'].iloc[-1]) - current_low
            
            if body_size > lower_wick * 1.5:  # Cuerpo mayor que wick inferior
                return 'short'

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