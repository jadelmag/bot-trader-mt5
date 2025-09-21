import pandas as pd

class CandlePatterns:
    """
    Clase que contiene listas de patrones de velas japonesas y métodos estáticos para detectar dichos patrones.
    """

    # --------------------------------------------------------------------------
    # Métodos Estáticos para la Detección de Patrones
    # --------------------------------------------------------------------------

    # --- Patrones de Una Vela ---
    
    @staticmethod
    def is_hammer(candles, index=-1):
        if index < 50: return None # Necesitamos datos para la EMA y el RSI

        df = pd.DataFrame(candles)
        
        # Calcular EMA 50 para el filtro de tendencia
        ema_50 = df['close'].ewm(span=50, adjust=False).mean()

        # Calcular RSI 14 para el filtro de momentum
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        candle = candles[index]
        body_size = abs(candle['close'] - candle['open'])
        if body_size == 0: return None

        lower_shadow = (candle['open'] - candle['low']) if candle['close'] > candle['open'] else (candle['close'] - candle['low'])
        upper_shadow = (candle['high'] - candle['close']) if candle['close'] > candle['open'] else (candle['high'] - candle['open'])
        
        # Comprobar forma de martillo + filtro de tendencia (bajo EMA50) + filtro de momentum (RSI < 35)
        is_hammer_shape = lower_shadow >= 2 * body_size and upper_shadow < body_size * 0.5
        is_downtrend = candle['close'] < ema_50.iloc[index]
        is_oversold = rsi.iloc[index] < 35

        if is_hammer_shape and is_downtrend and is_oversold:
            return 'long'
            
        return None

    @staticmethod
    def is_shooting_star(candles, index=-1):
        candle = candles[index]
        body_size = abs(candle['close'] - candle['open'])
        if body_size == 0: return None
        upper_shadow = (candle['high'] - candle['close']) if candle['close'] > candle['open'] else (candle['high'] - candle['open'])
        lower_shadow = (candle['open'] - candle['low']) if candle['close'] > candle['open'] else (candle['close'] - candle['low'])
        if upper_shadow >= 2 * body_size and lower_shadow < body_size * 0.5:
            if index > 0 and candles[index-1]['close'] > candles[index-1]['open']:
                return 'short'
        return None

    @staticmethod
    def is_marubozu(candles, index=-1):
        if index < 50: return None # Necesitamos suficientes datos para la EMA de 50

        # Convertir a DataFrame para calcular la EMA
        df = pd.DataFrame(candles)
        ema_50 = df['close'].ewm(span=50, adjust=False).mean()

        candle = candles[index]
        body_size = abs(candle['close'] - candle['open'])
        candle_range = candle['high'] - candle['low']
        
        if candle_range > 0 and body_size / candle_range > 0.98:
            # Filtro de tendencia:
            # Señal alcista solo si el cierre está por encima de la EMA 50
            if candle['close'] > candle['open'] and candle['close'] > ema_50.iloc[index]:
                return 'long'
            # Señal bajista solo si el cierre está por debajo de la EMA 50
            elif candle['open'] > candle['close'] and candle['close'] < ema_50.iloc[index]:
                return 'short'
        return None

    @staticmethod
    def is_dragonfly_doji(candles, index=-1):
        candle = candles[index]
        body_size = abs(candle['close'] - candle['open'])
        candle_range = candle['high'] - candle['low']
        if candle_range > 0 and body_size / candle_range < 0.15:
            if (candle['high'] - max(candle['close'], candle['open'])) / candle_range < 0.20:
                if index > 0 and candles[index-1]['close'] < candles[index-1]['open']:
                    return 'long'
        return None

    @staticmethod
    def is_gravestone_doji(candles, index=-1):
        if index < 50: return None # Necesitamos datos para la EMA

        df = pd.DataFrame(candles)
        ema_50 = df['close'].ewm(span=50, adjust=False).mean()

        candle = candles[index]
        body_size = abs(candle['close'] - candle['open'])
        candle_range = candle['high'] - candle['low']

        # Comprobar forma + tendencia alcista (sobre EMA50)
        is_gravestone_shape = candle_range > 0 and body_size / candle_range < 0.15 and (min(candle['close'], candle['open']) - candle['low']) / candle_range < 0.20
        is_uptrend = candle['close'] > ema_50.iloc[index]

        if is_gravestone_shape and is_uptrend:
            return 'short'

        return None

    @staticmethod
    def is_doji(candles, index=-1):
        candle = candles[index]
        body_size = abs(candle['close'] - candle['open'])
        candle_range = candle['high'] - candle['low']
        if candle_range > 0 and body_size / candle_range < 0.1:
            return 'neutral'
        return None

    @staticmethod
    def is_long_legged_doji(candles, index=-1):
        candle = candles[index]
        body_size = abs(candle['close'] - candle['open'])
        candle_range = candle['high'] - candle['low']
        if candle_range > 0 and body_size / candle_range < 0.1:
            upper_shadow = candle['high'] - max(candle['open'], candle['close'])
            lower_shadow = min(candle['open'], candle['close']) - candle['low']
            if upper_shadow > body_size * 2.5 and lower_shadow > body_size * 2.5:
                return 'neutral'
        return None

    @staticmethod
    def is_doji_reversal(candles, index=-1):
        if index < 1: return None  # Necesitamos al menos una vela anterior para determinar la tendencia
        candle = candles[index]
        prev_candle = candles[index - 1]

        body_size = abs(candle['close'] - candle['open'])
        candle_range = candle['high'] - candle['low']

        # Comprobar si es un Doji
        if candle_range > 0 and body_size / candle_range < 0.1:
            # Determinar la señal basada en la vela anterior
            if prev_candle['close'] < prev_candle['open']:  # Vela anterior es bajista
                return 'long'  # Posible reversión alcista
            elif prev_candle['close'] > prev_candle['open']:  # Vela anterior es alcista
                return 'short'  # Posible reversión bajista
        return None

    @staticmethod
    def is_hanging_man(candles, index=-1):
        candle = candles[index]
        body_size = abs(candle['close'] - candle['open'])
        if body_size == 0: return None
        lower_shadow = (candle['open'] - candle['low']) if candle['close'] > candle['open'] else (candle['close'] - candle['low'])
        upper_shadow = (candle['high'] - candle['close']) if candle['close'] > candle['open'] else (candle['high'] - candle['open'])
        if lower_shadow >= 2 * body_size and upper_shadow < body_size * 0.5:
            if index > 0 and candles[index-1]['close'] > candles[index-1]['open']:
                return 'short'
        return None

    @staticmethod
    def is_inverted_hammer(candles, index=-1):
        candle = candles[index]
        body_size = abs(candle['close'] - candle['open'])
        if body_size == 0: return None
        upper_shadow = (candle['high'] - candle['close']) if candle['close'] > candle['open'] else (candle['high'] - candle['open'])
        lower_shadow = (candle['open'] - candle['low']) if candle['close'] > candle['open'] else (candle['close'] - candle['low'])
        if upper_shadow >= 2 * body_size and lower_shadow < body_size * 0.5:
            if index > 0 and candles[index-1]['close'] < candles[index-1]['open']:
                return 'long'
        return None

    # --- Patrones de Dos Velas ---
    
    @staticmethod
    def is_engulfing(candles, index=-1):
        if index < 1: return None
        current_candle, prev_candle = candles[index], candles[index-1]
        if prev_candle['close'] < prev_candle['open'] and current_candle['close'] > current_candle['open'] and current_candle['close'] >= prev_candle['open'] and current_candle['open'] <= prev_candle['close']:
            return 'long'
        if prev_candle['close'] > prev_candle['open'] and current_candle['close'] < current_candle['open'] and current_candle['open'] >= prev_candle['close'] and current_candle['close'] <= prev_candle['open']:
            return 'short'
        return None

    @staticmethod
    def is_harami(candles, index=-1):
        if index < 50: return None # Necesitamos datos para la EMA de 50

        df = pd.DataFrame(candles)
        ema_50 = df['close'].ewm(span=50, adjust=False).mean()

        current_candle, prev_candle = candles[index], candles[index-1]
        prev_body_size = abs(prev_candle['close'] - prev_candle['open'])
        current_body_size = abs(current_candle['close'] - current_candle['open'])
        
        # Restauramos la condición original para detectar solo patrones fuertes
        if prev_body_size < current_body_size * 2: return None

        # Harami Alcista (long): vela anterior bajista, actual alcista, dentro de la anterior.
        # Y ADEMÁS, el precio está por debajo de la EMA50 (buscando reversión de tendencia bajista).
        is_bullish_harami = prev_candle['close'] < prev_candle['open'] and current_candle['close'] > current_candle['open'] and current_candle['open'] > prev_candle['close'] and current_candle['close'] < prev_candle['open']
        if is_bullish_harami and current_candle['close'] < ema_50.iloc[index]:
            return 'long'

        # Harami Bajista (short): vela anterior alcista, actual bajista, dentro de la anterior.
        # Y ADEMÁS, el precio está por encima de la EMA50 (buscando reversión de tendencia alcista).
        is_bearish_harami = prev_candle['close'] > prev_candle['open'] and current_candle['close'] < current_candle['open'] and current_candle['open'] < prev_candle['close'] and current_candle['close'] > prev_candle['open']
        if is_bearish_harami and current_candle['close'] > ema_50.iloc[index]:
            return 'short'
            
        return None

    @staticmethod
    def is_piercing_line(candles, index=-1):
        if index < 1: return None
        c1, c2 = candles[index-1], candles[index]
        if not (c1['close'] < c1['open'] and c2['close'] > c2['open']): return None
        mid_point_c1 = (c1['open'] + c1['close']) / 2
        if c2['open'] < c1['close'] and c2['close'] > mid_point_c1:
            return 'long'
        return None

    @staticmethod
    def is_dark_cloud_cover(candles, index=-1):
        if index < 50: return None # Necesitamos datos para la EMA y el RSI

        df = pd.DataFrame(candles)
        
        # Calcular EMA 50 para el filtro de tendencia
        ema_50 = df['close'].ewm(span=50, adjust=False).mean()

        # Calcular RSI 14 para el filtro de momentum
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        c1, c2 = candles[index-1], candles[index]

        # Comprobar forma + tendencia alcista (sobre EMA50) + momentum sobrecomprado (RSI > 65)
        is_dark_cloud_shape = (c1['close'] > c1['open'] and c2['close'] < c2['open']) and (c2['open'] > c1['close'] and c2['close'] < (c1['open'] + c1['close']) / 2)
        is_uptrend = c1['close'] > ema_50.iloc[index-1]
        is_overbought = rsi.iloc[index] > 65

        if is_dark_cloud_shape and is_uptrend and is_overbought:
            return 'short'

        return None

    
    # --- Patrones de Tres Velas ---
    
    @staticmethod
    def is_morning_star(candles, index=-1):
        if index < 2: return None
        c1, c2, c3 = candles[index-2], candles[index-1], candles[index]
        c1_is_bearish = c1['close'] < c1['open']
        c1_body = abs(c1['open'] - c1['close'])
        c2_body = abs(c2['open'] - c2['close'])
        star_opens_lower = c2['open'] < c1['close']
        c3_is_bullish = c3['close'] > c3['open']
        c3_closes_in_c1 = c3['close'] > (c1['open'] + c1['close']) / 2
        if c1_is_bearish and c1_body > c2_body * 1.5 and star_opens_lower and c3_is_bullish and c3_closes_in_c1:
            return 'long'
        return None

    @staticmethod
    def is_evening_star(candles, index=-1):
        if index < 2: return None
        c1, c2, c3 = candles[index-2], candles[index-1], candles[index]
        c1_is_bullish = c1['close'] > c1['open']
        c1_body = abs(c1['open'] - c1['close'])
        c2_body = abs(c2['open'] - c2['close'])
        star_opens_higher = c2['open'] > c1['close']
        c3_is_bearish = c3['close'] < c3['open']
        c3_closes_in_c1 = c3['close'] < (c1['open'] + c1['close']) / 2
        if c1_is_bullish and c1_body > c2_body * 1.5 and star_opens_higher and c3_is_bearish and c3_closes_in_c1:
            return 'short'
        return None

    @staticmethod
    def is_three_white_soldiers(candles, index=-1):
        if index < 2: return None
        c1, c2, c3 = candles[index-2], candles[index-1], candles[index]
        are_bullish = c1['close'] > c1['open'] and c2['close'] > c2['open'] and c3['close'] > c3['open']
        if not are_bullish: return None
        opens_in_body = c2['open'] > c1['open'] and c2['open'] < c1['close'] and c3['open'] > c2['open'] and c3['open'] < c2['close']
        closes_higher = c2['close'] > c1['close'] and c3['close'] > c2['close']
        if opens_in_body and closes_higher:
            return 'long'
        return None

    @staticmethod
    def is_three_black_crows(candles, index=-1):
        if index < 2: return None
        c1, c2, c3 = candles[index-2], candles[index-1], candles[index]
        are_bearish = c1['close'] < c1['open'] and c2['close'] < c2['open'] and c3['close'] < c3['open']
        if not are_bearish: return None
        opens_in_body = c2['open'] < c1['open'] and c2['open'] > c1['close'] and c3['open'] < c2['open'] and c3['open'] > c2['close']
        closes_lower = c2['close'] < c1['close'] and c3['close'] < c2['close']
        if opens_in_body and closes_lower:
            return 'short'
        return None

    @staticmethod
    def is_three_inside_up_down(candles, index=-1):
        if index < 2: return None
        c1, c2, c3 = candles[index-2], candles[index-1], candles[index]
        is_harami_up = c1['close'] < c1['open'] and c2['close'] > c2['open'] and c2['open'] > c1['close'] and c2['close'] < c1['open']
        if is_harami_up and c3['close'] > c1['open']:
            return 'long'
        is_harami_down = c1['close'] > c1['open'] and c2['close'] < c2['open'] and c2['open'] < c1['close'] and c2['close'] > c1['open']
        if is_harami_down and c3['close'] < c1['open']:
            return 'short'
        return None

    @staticmethod
    def is_three_outside_up_down(candles, index=-1):
        if index < 2: return None
        c1, c2, c3 = candles[index-2], candles[index-1], candles[index]
        is_engulfing_up = c1['close'] < c1['open'] and c2['close'] > c2['open'] and c2['close'] >= c1['open'] and c2['open'] <= c1['close']
        if is_engulfing_up and c3['close'] > c2['close']:
            return 'long'
        is_engulfing_down = c1['close'] > c1['open'] and c2['close'] < c2['open'] and c2['open'] >= c1['close'] and c2['close'] <= c1['open']
        if is_engulfing_down and c3['close'] < c2['close']:
            return 'short'
        return None

    
    # --- Patrones de Cinco Velas ---
    
    @staticmethod
    def is_rising_three_methods(candles, index=-1):
        if index < 4: return None
        c1, c2, c3, c4, c5 = candles[index-4:index+1]
        c1_bullish = c1['close'] > c1['open']
        c5_bullish = c5['close'] > c5['open']
        three_bearish = c2['close'] < c2['open'] and c3['close'] < c3['open'] and c4['close'] < c4['open']
        contained = all(max(c['open'], c['close']) < c1['high'] and min(c['open'], c['close']) > c1['low'] for c in [c2, c3, c4])
        c5_closes_higher = c5['close'] > c1['close']
        if c1_bullish and c5_bullish and three_bearish and contained and c5_closes_higher:
            return 'long'
        return None

    @staticmethod
    def is_falling_three_methods(candles, index=-1):
        if index < 4: return None
        c1, c2, c3, c4, c5 = candles[index-4:index+1]
        c1_bearish = c1['close'] < c1['open']
        c5_bearish = c5['close'] < c5['open']
        three_bullish = c2['close'] > c2['open'] and c3['close'] > c3['open'] and c4['close'] > c4['open']
        contained = all(max(c['open'], c['close']) < c1['high'] and min(c['open'], c['close']) > c1['low'] for c in [c2, c3, c4])
        c5_closes_lower = c5['close'] < c1['close']
        if c1_bearish and c5_bearish and three_bullish and contained and c5_closes_lower:
            return 'short'
        return None

    # --------------------------------------------------------------------------
    # Método Principal de Detección
    # --------------------------------------------------------------------------

    @staticmethod
    def detect_all_patterns(candles, index=-1):
        all_pattern_functions = [
            CandlePatterns.is_hammer, CandlePatterns.is_shooting_star, CandlePatterns.is_marubozu,
            CandlePatterns.is_dragonfly_doji, CandlePatterns.is_gravestone_doji, CandlePatterns.is_hanging_man,
            CandlePatterns.is_inverted_hammer, CandlePatterns.is_doji, CandlePatterns.is_long_legged_doji,
            CandlePatterns.is_doji_reversal, 
            CandlePatterns.is_engulfing, CandlePatterns.is_harami, CandlePatterns.is_piercing_line,
            CandlePatterns.is_dark_cloud_cover, CandlePatterns.is_morning_star, CandlePatterns.is_evening_star,
            CandlePatterns.is_three_white_soldiers, CandlePatterns.is_three_black_crows,
            CandlePatterns.is_three_inside_up_down, CandlePatterns.is_three_outside_up_down,
            CandlePatterns.is_rising_three_methods, CandlePatterns.is_falling_three_methods
        ]
        
        signals = {'long': [], 'short': [], 'neutral': []}
        for pattern_func in all_pattern_functions:
            result = pattern_func(candles, index)
            if result:
                pattern_name = pattern_func.__name__.replace('is_', '')
                if result in signals:
                    signals[result].append(pattern_name)
        return signals