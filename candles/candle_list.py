import pandas as pd
import numpy as np

class CandlePatterns:
    """
    Clase que contiene patrones de velas japonesas optimizados para timeframe M1.
    Incluye filtros adicionales de tendencia, momentum y niveles de precio.
    """
    
    # Constante para el control de operaciones
    MAX_CANDLES_IN_TRADE = 2  # Cierre automático a las 2 velas

    # --------------------------------------------------------------------------
    # Métodos Utilitarios para Indicadores y Filtros
    # --------------------------------------------------------------------------
    
    @staticmethod
    def _is_support(candles, index, lookback=3):  # Reducido de 5 a 3
        if index < lookback: return False
        
        current_low = candles[index]['low']
        for i in range(index-lookback, index):
            if candles[i]['low'] < current_low * 1.001:  # Aumentada tolerancia de 0.0005 a 0.001
                return False
        return True
    
    @staticmethod
    def _is_resistance(candles, index, lookback=3):  # Reducido de 5 a 3
        """Verifica si el precio actual está en un nivel de resistencia"""
        if index < lookback: return False
        
        current_high = candles[index]['high']
        for i in range(index-lookback, index):
            if candles[i]['high'] > current_high * 0.999:  # Aumentada tolerancia de 0.9995 a 0.999
                return False
        return True
    
    @staticmethod
    def _get_m5_trend(candles, index):
        """Simula la tendencia de M5 agrupando velas de M1"""
        if index < 20: return "neutral"  # Reducido de 20 a 15 para menos restricción
        
        # Crear bloques de 5 velas
        m5_closes = []
        for i in range(max(0, index-20), index+1, 5):
            if i+4 <= index:  # Asegurar que hay 5 velas completas
                block = candles[i:i+5]
                m5_closes.append(block[-1]['close'])
        
        if len(m5_closes) < 3: return "neutral"
        
        # Determinar tendencia en M5
        if m5_closes[-1] > m5_closes[-2] > m5_closes[-3]:
            return "bullish"
        elif m5_closes[-1] < m5_closes[-2] < m5_closes[-3]:
            return "bearish"
            
        return "neutral"

    @staticmethod
    def _check_volume_confirmation(candles, index):
        """Verifica si hay confirmación de volumen (volumen creciente)"""
        if index < 2: return False
        
        # Verificar si existe la clave 'volume' en los datos de velas
        try:
            return candles[index]['volume'] > 1.1 * candles[index-1]['volume']  # Relajado de 1.2 a 1.1
        except (KeyError, TypeError):
            # Si no hay datos de volumen, devolver True para no bloquear patrones
            return True

    # --------------------------------------------------------------------------
    # Métodos Estáticos para la Detección de Patrones (Optimizados para M1)
    # --------------------------------------------------------------------------
    
    # --- Patrones de Una Vela ---
    
    @staticmethod
    def is_hammer(candles, index=-1):
        """Martillo: sombra inferior larga, cuerpo pequeño, en soporte"""
        if index < 20: return None
        
        df = pd.DataFrame(candles)
        ema_50 = df['close'].ewm(span=50, adjust=False).mean()
        
        # Calcular RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        candle = candles[index]
        body_size = abs(candle['close'] - candle['open'])
        lower_shadow = (candle['open'] - candle['low']) if candle['close'] > candle['open'] else (candle['close'] - candle['low'])
        upper_shadow = (candle['high'] - candle['close']) if candle['close'] > candle['open'] else (candle['high'] - candle['open'])
        
        # Filtros optimizados para M1
        is_hammer_shape = lower_shadow >= 2 * body_size and upper_shadow < body_size * 0.5
        is_downtrend = candle['close'] < ema_50.iloc[index]
        is_oversold = rsi.iloc[index] < 40  # Relajado de 30 a 40
        is_support = CandlePatterns._is_support(candles, index)
        
        if is_hammer_shape and is_downtrend and is_oversold and is_support:
            # Verificar tendencia en M5 (comentado para ser menos restrictivo)
            # if CandlePatterns._get_m5_trend(candles, index) != "bearish":
            return 'long'
            
        return None

    @staticmethod
    def is_shooting_star(candles, index=-1):
        """Estrella fugaz: sombra superior larga, cuerpo pequeño, en resistencia"""
        if index < 20: return None
        
        df = pd.DataFrame(candles)
        ema_50 = df['close'].ewm(span=50, adjust=False).mean()
        
        # Calcular RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        candle = candles[index]
        body_size = abs(candle['close'] - candle['open'])
        upper_shadow = (candle['high'] - candle['close']) if candle['close'] > candle['open'] else (candle['high'] - candle['open'])
        lower_shadow = (candle['open'] - candle['low']) if candle['close'] > candle['open'] else (candle['close'] - candle['low'])
        
        # Filtros optimizados para M1
        is_shooting_star_shape = upper_shadow >= 2 * body_size and lower_shadow < body_size * 0.5
        is_uptrend = candle['close'] > ema_50.iloc[index]
        is_overbought = rsi.iloc[index] > 60  # Relajado de 70 a 60
        is_resistance = CandlePatterns._is_resistance(candles, index)
        
        if is_shooting_star_shape and is_uptrend and is_overbought and is_resistance:
            # Verificar tendencia en M5 (comentado para ser menos restrictivo)
            # if CandlePatterns._get_m5_trend(candles, index) != "bullish":
            return 'short'
            
        return None

    @staticmethod
    def is_marubozu(candles, index=-1):
        """Marubozu: vela sin sombras (cuerpo completo)"""
        if index < 20: return None
        
        df = pd.DataFrame(candles)
        ema_50 = df['close'].ewm(span=50, adjust=False).mean()
        ema_200 = df['close'].ewm(span=200, adjust=False).mean()
        
        # Calcular RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        candle = candles[index]
        body_size = abs(candle['close'] - candle['open'])
        candle_range = candle['high'] - candle['low']
        
        # Verificar forma de marubozu
        is_marubozu_shape = candle_range > 0 and body_size / candle_range > 0.95
        if not is_marubozu_shape: return None
        
        # Usarlo como señal de reversión (contra la tendencia excesiva)
        # Marubozu alcista como señal bajista (exceso alcista)
        if (candle['close'] > candle['open'] and      # Vela alcista
            candle['close'] > ema_50.iloc[index] and  # Por encima de EMA50
            rsi.iloc[index] > 65 and                  # Relajado de 75 a 65
            CandlePatterns._is_resistance(candles, index)):
            return 'short'
        
        # Marubozu bajista como señal alcista (exceso bajista)
        elif (candle['open'] > candle['close'] and     # Vela bajista
              candle['close'] < ema_50.iloc[index] and # Por debajo de EMA50
              rsi.iloc[index] < 35 and                 # Relajado de 25 a 35
              CandlePatterns._is_support(candles, index)):
            return 'long'
            
        return None

    @staticmethod
    def is_dragonfly_doji(candles, index=-1):
        """Doji libélula: cuerpo pequeño, sombra inferior larga, sin sombra superior"""
        if index < 20: return None
        
        df = pd.DataFrame(candles)
        ema_50 = df['close'].ewm(span=50, adjust=False).mean()
        
        # Calcular RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        candle = candles[index]
        body_size = abs(candle['close'] - candle['open'])
        candle_range = candle['high'] - candle['low']
        
        if candle_range > 0 and body_size / candle_range < 0.15:
            if (candle['high'] - max(candle['close'], candle['open'])) / candle_range < 0.20:
                # Filtros adicionales para M1
                is_downtrend = candle['close'] < ema_50.iloc[index]
                is_oversold = rsi.iloc[index] < 40  # Relajado de 30 a 40
                is_support = CandlePatterns._is_support(candles, index)
                has_volume = CandlePatterns._check_volume_confirmation(candles, index)
                
                if is_downtrend and is_oversold and is_support and has_volume:
                    # Verificar tendencia en M5 (comentado para ser menos restrictivo)
                    # if CandlePatterns._get_m5_trend(candles, index) != "bearish":
                    return 'long'
        return None

    @staticmethod
    def is_gravestone_doji(candles, index=-1):
        """Doji lápida: cuerpo pequeño, sombra superior larga, sin sombra inferior"""
        if index < 20: return None
        
        df = pd.DataFrame(candles)
        ema_50 = df['close'].ewm(span=50, adjust=False).mean()
        
        # Calcular RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        candle = candles[index]
        body_size = abs(candle['close'] - candle['open'])
        candle_range = candle['high'] - candle['low']
        
        is_gravestone_shape = (candle_range > 0 and 
                            body_size / candle_range < 0.15 and 
                            (min(candle['close'], candle['open']) - candle['low']) / candle_range < 0.20)
        
        if is_gravestone_shape:
            # Filtros adicionales para M1
            is_uptrend = candle['close'] > ema_50.iloc[index]
            is_overbought = rsi.iloc[index] > 60  # Relajado de 70 a 60
            is_resistance = CandlePatterns._is_resistance(candles, index)
            has_volume = CandlePatterns._check_volume_confirmation(candles, index)
            
            if is_uptrend and is_overbought and is_resistance and has_volume:
                # Verificar tendencia en M5 (comentado para ser menos restrictivo)
                # if CandlePatterns._get_m5_trend(candles, index) != "bullish":
                return 'short'
        
        return None

    @staticmethod
    def is_doji(candles, index=-1):
        """Doji: cuerpo muy pequeño, apertura y cierre casi idénticos"""
        if index < 20: return None
        
        df = pd.DataFrame(candles)
        ema_50 = df['close'].ewm(span=50, adjust=False).mean()
        
        # Calcular RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        candle = candles[index]
        body_size = abs(candle['close'] - candle['open'])
        candle_range = candle['high'] - candle['low']
        
        # Forma básica de doji (cuerpo extremadamente pequeño)
        if not (candle_range > 0 and body_size / candle_range < 0.05):
            return None
        
        # Para que sea relevante, debe estar en un punto de indecisión significativo
        
        # Para LONG: en soporte, RSI bajo, tendencia bajista
        if (candle['close'] < ema_50.iloc[index] and
            rsi.iloc[index] < 40 and  # Ya está en 40
            CandlePatterns._is_support(candles, index) and
            CandlePatterns._check_volume_confirmation(candles, index)):
            return 'long'
        
        # Para SHORT: en resistencia, RSI alto, tendencia alcista
        if (candle['close'] > ema_50.iloc[index] and
            rsi.iloc[index] > 60 and  # Ya está en 60
            CandlePatterns._is_resistance(candles, index) and
            CandlePatterns._check_volume_confirmation(candles, index)):
            return 'short'
        
        # Si no hay señal clara, pero es un doji
        return 'neutral'

    @staticmethod
    def is_long_legged_doji(candles, index=-1):
        """Doji patas largas: cuerpo pequeño, largas sombras superior e inferior"""
        if index < 20: return None
        
        df = pd.DataFrame(candles)
        ema_50 = df['close'].ewm(span=50, adjust=False).mean()
        
        # Calcular RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        candle = candles[index]
        body_size = abs(candle['close'] - candle['open'])
        candle_range = candle['high'] - candle['low']
        
        # Filtro de Forma
        is_doji_shape = candle_range > 0 and body_size / candle_range < 0.1
        if not is_doji_shape: return None
        
        upper_shadow = candle['high'] - max(candle['open'], candle['close'])
        lower_shadow = min(candle['open'], candle['close']) - candle['low']
        is_long_legged = upper_shadow > body_size * 2.5 and lower_shadow > body_size * 2.5
        if not is_long_legged: return None
        
        # Para LONG: tendencia bajista, RSI bajo y en soporte
        if (candle['close'] < ema_50.iloc[index] and
            rsi.iloc[index] < 40 and  # Relajado de 30 a 40
            CandlePatterns._is_support(candles, index) and
            CandlePatterns._check_volume_confirmation(candles, index)):
            # Verificar tendencia en M5 (comentado para ser menos restrictivo)
            # if CandlePatterns._get_m5_trend(candles, index) != "bearish":
            return 'long'
        
        # Para SHORT: tendencia alcista, RSI alto y en resistencia
        if (candle['close'] > ema_50.iloc[index] and
            rsi.iloc[index] > 60 and  # Relajado de 70 a 60
            CandlePatterns._is_resistance(candles, index) and
            CandlePatterns._check_volume_confirmation(candles, index)):
            # Verificar tendencia en M5 (comentado para ser menos restrictivo)
            # if CandlePatterns._get_m5_trend(candles, index) != "bullish":
            return 'short'
        
        return None

    @staticmethod
    def is_doji_reversal(candles, index=-1):
        """Doji de reversión: doji que marca un posible cambio de tendencia"""
        if index < 20: return None
        
        df = pd.DataFrame(candles)
        ema_50 = df['close'].ewm(span=50, adjust=False).mean()
        
        # Calcular RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        candle = candles[index]
        prev_candle = candles[index - 1]
        
        body_size = abs(candle['close'] - candle['open'])
        candle_range = candle['high'] - candle['low']
        
        # Forma de doji
        if not (candle_range > 0 and body_size / candle_range < 0.1):
            return None
        
        # Para señal LONG: tendencia bajista, RSI bajo, vela previa bajista, en soporte
        if (prev_candle['close'] < prev_candle['open'] and  # Vela previa bajista
            candle['close'] < ema_50.iloc[index] and        # Tendencia bajista
            rsi.iloc[index] < 40 and                        # Relajado de 35 a 40
            CandlePatterns._is_support(candles, index) and  # En soporte
            CandlePatterns._check_volume_confirmation(candles, index)):
            # Verificar tendencia en M5 (comentado para ser menos restrictivo)
            # if CandlePatterns._get_m5_trend(candles, index) != "bearish":
            return 'long'
        
        # Para señal SHORT: tendencia alcista, RSI alto, vela previa alcista, en resistencia
        if (prev_candle['close'] > prev_candle['open'] and  # Vela previa alcista
            candle['close'] > ema_50.iloc[index] and        # Tendencia alcista
            rsi.iloc[index] > 60 and                        # Relajado de 65 a 60
            CandlePatterns._is_resistance(candles, index) and # En resistencia
            CandlePatterns._check_volume_confirmation(candles, index)):
            # Verificar tendencia en M5 (comentado para ser menos restrictivo)
            # if CandlePatterns._get_m5_trend(candles, index) != "bullish":
            return 'short'
        
        return None

    @staticmethod
    def is_hanging_man(candles, index=-1):
        """Hombre colgado: similar al martillo pero en tendencia alcista"""
        if index < 20: return None
        
        df = pd.DataFrame(candles)
        ema_50 = df['close'].ewm(span=50, adjust=False).mean()
        
        # Calcular RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        candle = candles[index]
        body_size = abs(candle['close'] - candle['open'])
        
        lower_shadow = (candle['open'] - candle['low']) if candle['close'] > candle['open'] else (candle['close'] - candle['low'])
        upper_shadow = (candle['high'] - candle['close']) if candle['close'] > candle['open'] else (candle['high'] - candle['open'])
        
        # Filtros para M1
        is_hanging_man_shape = lower_shadow >= 2 * body_size and upper_shadow < body_size * 0.5
        is_uptrend = candle['close'] > ema_50.iloc[index]
        is_overbought = rsi.iloc[index] > 60  # Relajado de 65 a 60
        is_resistance = CandlePatterns._is_resistance(candles, index)
        has_volume = CandlePatterns._check_volume_confirmation(candles, index)
        
        if is_hanging_man_shape and is_uptrend and is_overbought and is_resistance and has_volume:
            # Verificar tendencia en M5 (comentado para ser menos restrictivo)
            # if CandlePatterns._get_m5_trend(candles, index) != "bullish":
            return 'short'
        
        return None

    @staticmethod
    def is_inverted_hammer(candles, index=-1):
        """Martillo invertido: cuerpo pequeño con larga sombra superior"""
        if index < 20: return None
        
        df = pd.DataFrame(candles)
        ema_50 = df['close'].ewm(span=50, adjust=False).mean()
        
        # Calcular RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        candle = candles[index]
        body_size = abs(candle['close'] - candle['open'])
        upper_shadow = (candle['high'] - candle['close']) if candle['close'] > candle['open'] else (candle['high'] - candle['open'])
        lower_shadow = (candle['open'] - candle['low']) if candle['close'] > candle['open'] else (candle['close'] - candle['low'])
        
        # Filtros para M1
        is_inverted_hammer_shape = upper_shadow >= 2 * body_size and lower_shadow < body_size * 0.5
        is_downtrend = candle['close'] < ema_50.iloc[index]
        is_oversold = rsi.iloc[index] < 40  # Relajado de 30 a 40
        is_support = CandlePatterns._is_support(candles, index)
        has_volume = CandlePatterns._check_volume_confirmation(candles, index)
        
        if is_inverted_hammer_shape and is_downtrend and is_oversold and is_support and has_volume:
            # Verificar tendencia en M5 (comentado para ser menos restrictivo)
            # if CandlePatterns._get_m5_trend(candles, index) != "bearish":
            return 'long'
        
        return None

    # --- Patrones de Dos Velas ---
    
    @staticmethod
    def is_engulfing(candles, index=-1):
        """Patrón de vela envolvente: una vela envuelve completamente a la anterior"""
        if index < 20: return None
        
        df = pd.DataFrame(candles)
        ema_50 = df['close'].ewm(span=50, adjust=False).mean()
        
        # Calcular RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        current_candle, prev_candle = candles[index], candles[index-1]
        
        # Envolvente Alcista con filtros
        is_bullish_shape = (prev_candle['close'] < prev_candle['open'] and 
                           current_candle['close'] > current_candle['open'] and 
                           current_candle['close'] >= prev_candle['open'] and 
                           current_candle['open'] <= prev_candle['close'])
                           
        if (is_bullish_shape and 
            current_candle['close'] < ema_50.iloc[index] and
            rsi.iloc[index] < 40 and
            CandlePatterns._is_support(candles, index) and
            CandlePatterns._check_volume_confirmation(candles, index)):
            return 'long'
        
        # Envolvente Bajista con filtros
        is_bearish_shape = (prev_candle['close'] > prev_candle['open'] and 
                           current_candle['close'] < current_candle['open'] and 
                           current_candle['open'] >= prev_candle['close'] and 
                           current_candle['close'] <= prev_candle['open'])
                           
        if (is_bearish_shape and 
            current_candle['close'] > ema_50.iloc[index] and
            rsi.iloc[index] > 60 and
            CandlePatterns._is_resistance(candles, index) and
            CandlePatterns._check_volume_confirmation(candles, index)):
            return 'short'
        
        return None
    
    @staticmethod
    def is_harami(candles, index=-1):
        """Harami: vela contenida completamente dentro del cuerpo de la anterior"""
        if index < 20: return None
        
        df = pd.DataFrame(candles)
        ema_50 = df['close'].ewm(span=50, adjust=False).mean()
        
        # Calcular RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        current_candle, prev_candle = candles[index], candles[index-1]
        prev_body_size = abs(prev_candle['close'] - prev_candle['open'])
        current_body_size = abs(current_candle['close'] - current_candle['open'])
        
        # Verificar forma de harami (cuerpo pequeño dentro del anterior)
        if prev_body_size < current_body_size * 2:
            return None
        
        # Harami Alcista (long) con filtros
        is_bullish_harami = (prev_candle['close'] < prev_candle['open'] and 
                            current_candle['close'] > current_candle['open'] and 
                            current_candle['open'] > prev_candle['close'] and 
                            current_candle['close'] < prev_candle['open'])
                            
        if (is_bullish_harami and 
            current_candle['close'] < ema_50.iloc[index] and
            rsi.iloc[index] < 40 and
            CandlePatterns._is_support(candles, index) and
            CandlePatterns._check_volume_confirmation(candles, index)):
            return 'long'
        
        # Harami Bajista (short) con filtros
        is_bearish_harami = (prev_candle['close'] > prev_candle['open'] and 
                            current_candle['close'] < current_candle['open'] and 
                            current_candle['open'] < prev_candle['close'] and 
                            current_candle['close'] > prev_candle['open'])
                            
        if (is_bearish_harami and 
            current_candle['close'] > ema_50.iloc[index] and
            rsi.iloc[index] > 60 and
            CandlePatterns._is_resistance(candles, index) and
            CandlePatterns._check_volume_confirmation(candles, index)):
            return 'short'
        
        return None

    @staticmethod
    def is_piercing_line(candles, index=-1):
        """Línea penetrante: vela alcista que cierra más de la mitad de la vela bajista anterior"""
        if index < 20: return None
        
        df = pd.DataFrame(candles)
        ema_50 = df['close'].ewm(span=50, adjust=False).mean()
        
        # Calcular RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        c1, c2 = candles[index-1], candles[index]
        
        # Verificar forma básica del patrón
        if not (c1['close'] < c1['open'] and c2['close'] > c2['open']):
            return None
        
        mid_point_c1 = (c1['open'] + c1['close']) / 2
        
        # Filtros optimizados para M1
        if (c2['open'] < c1['close'] and 
            c2['close'] > mid_point_c1 and
            c2['close'] < ema_50.iloc[index] and   # Tendencia bajista
            rsi.iloc[index] < 40 and               # Relajado de 30-35 a 40
            CandlePatterns._is_support(candles, index) and  # En soporte
            CandlePatterns._check_volume_confirmation(candles, index)):
            return 'long'
        
        return None

    @staticmethod
    def is_dark_cloud_cover(candles, index=-1):
        """Cubierta de nube oscura: vela bajista que penetra más de la mitad de la vela alcista anterior"""
        if index < 20: return None
        
        df = pd.DataFrame(candles)
        ema_50 = df['close'].ewm(span=50, adjust=False).mean()
        
        # Calcular RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        c1, c2 = candles[index-1], candles[index]
        
        # Filtros optimizados para M1
        is_dark_cloud_shape = (c1['close'] > c1['open'] and 
                            c2['close'] < c2['open'] and 
                            c2['open'] > c1['high'] and 
                            c2['close'] < (c1['open'] + c1['close']) / 2)
                            
        if (is_dark_cloud_shape and 
            c2['close'] > ema_50.iloc[index] and       # Tendencia alcista
            rsi.iloc[index] > 60 and                   # Relajado de 65 a 60
            CandlePatterns._is_resistance(candles, index) and  # En resistencia
            CandlePatterns._check_volume_confirmation(candles, index)):
            return 'short'
                
        return None

    # --- Patrones de Tres Velas ---

    @staticmethod
    def is_morning_star(candles, index=-1):
        """Estrella de la mañana: patrón alcista de reversión de tres velas"""
        if index < 20: return None
        
        # Necesitamos al menos 3 velas para este patrón
        if index < 2: return None
        
        df = pd.DataFrame(candles)
        ema_50 = df['close'].ewm(span=50, adjust=False).mean()
        
        # Calcular RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        c1, c2, c3 = candles[index-2], candles[index-1], candles[index]
        
        # Verificar forma básica
        c1_is_bearish = c1['close'] < c1['open']
        c1_body = abs(c1['open'] - c1['close'])
        c2_body = abs(c2['open'] - c2['close'])
        star_small_body = c2_body < c1_body * 0.5  # La estrella debe tener cuerpo pequeño
        c3_is_bullish = c3['close'] > c3['open']
        c3_closes_in_c1 = c3['close'] > (c1['open'] + c1['close']) / 2  # Cierra en cuerpo de c1
        
        # Filtros adicionales para M1
        is_downtrend = c1['close'] < ema_50.iloc[index-2]
        is_oversold = rsi.iloc[index] < 40  # Relajado de 35 a 40
        is_support = CandlePatterns._is_support(candles, index)
        has_volume_confirmation = CandlePatterns._check_volume_confirmation(candles, index)
        
        # Criterios optimizados
        if (c1_is_bearish and 
            c1_body > c2_body * 1.5 and 
            star_small_body and 
            c3_is_bullish and 
            c3_closes_in_c1 and
            is_downtrend and 
            is_oversold and 
            is_support and 
            has_volume_confirmation):
            return 'long'
            
        return None

    @staticmethod
    def is_evening_star(candles, index=-1):
        """Estrella de la tarde: patrón bajista de reversión de tres velas"""
        if index < 20: return None
        
        # Necesitamos al menos 3 velas para este patrón
        if index < 2: return None
        
        df = pd.DataFrame(candles)
        ema_50 = df['close'].ewm(span=50, adjust=False).mean()
        
        # Calcular RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        c1, c2, c3 = candles[index-2], candles[index-1], candles[index]
        
        # Verificar forma básica
        c1_is_bullish = c1['close'] > c1['open']
        c1_body = abs(c1['open'] - c1['close'])
        c2_body = abs(c2['open'] - c2['close'])
        star_small_body = c2_body < c1_body * 0.5  # La estrella debe tener cuerpo pequeño
        c3_is_bearish = c3['close'] < c3['open']
        c3_closes_in_c1 = c3['close'] < (c1['open'] + c1['close']) / 2  # Cierra en cuerpo de c1
        
        # Filtros adicionales para M1
        is_uptrend = c1['close'] > ema_50.iloc[index-2]
        is_overbought = rsi.iloc[index] > 60  # Relajado de 65 a 60
        is_resistance = CandlePatterns._is_resistance(candles, index)
        has_volume_confirmation = CandlePatterns._check_volume_confirmation(candles, index)
        
        # Criterios optimizados
        if (c1_is_bullish and 
            c1_body > c2_body * 1.5 and 
            star_small_body and 
            c3_is_bearish and 
            c3_closes_in_c1 and
            is_uptrend and 
            is_overbought and 
            is_resistance and 
            has_volume_confirmation):
            return 'short'
            
        return None

    @staticmethod
    def is_three_white_soldiers(candles, index=-1):
        """Tres soldados blancos: tres velas alcistas consecutivas"""
        if index < 20: return None
        
        if index < 2: return None
        
        df = pd.DataFrame(candles)
        ema_50 = df['close'].ewm(span=50, adjust=False).mean()
        
        # Calcular RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        c1, c2, c3 = candles[index-2], candles[index-1], candles[index]
        
        # Verificar que todas las velas son alcistas
        are_bullish = c1['close'] > c1['open'] and c2['close'] > c2['open'] and c3['close'] > c3['open']
        if not are_bullish: return None
        
        # Verificar cuerpos significativos (no deben ser dojis)
        c1_range = c1['high'] - c1['low']
        c2_range = c2['high'] - c2['low']
        c3_range = c3['high'] - c3['low']
        c1_body = abs(c1['close'] - c1['open'])
        c2_body = abs(c2['close'] - c2['open'])
        c3_body = abs(c3['close'] - c3['open'])
        
        are_strong = (c1_body > c1_range * 0.5 and 
                    c2_body > c2_range * 0.5 and 
                    c3_body > c3_range * 0.5)
        
        # Verificar que cada vela abre dentro del cuerpo de la anterior y cierra más alto
        opens_in_body = (c2['open'] > c1['open'] and 
                        c2['open'] < c1['close'] and 
                        c3['open'] > c2['open'] and 
                        c3['open'] < c2['close'])
        
        closes_higher = c2['close'] > c1['close'] and c3['close'] > c2['close']
        
        # Filtros adicionales para M1
        is_support = CandlePatterns._is_support(candles, index-2)  # Formación inicia en soporte
        is_downtrend = c1['open'] < ema_50.iloc[index-2]  # Inicia en tendencia bajista
        is_not_overbought = rsi.iloc[index] < 70  # No hay sobrecompra extrema al final
        
        # Verificar volumen creciente (con manejo de errores)
        try:
            has_volume_confirmation = (c1['volume'] < c2['volume'] and c2['volume'] < c3['volume'])
        except (KeyError, TypeError):
            has_volume_confirmation = True  # Si no hay datos de volumen, no bloqueamos
        
        if (are_bullish and 
            are_strong and 
            opens_in_body and 
            closes_higher and
            is_support and 
            is_downtrend and 
            is_not_overbought and 
            has_volume_confirmation):
            return 'long'
        
        return None

    @staticmethod
    def is_three_black_crows(candles, index=-1):
        """Tres cuervos negros: tres velas bajistas consecutivas"""
        if index < 20: return None
        
        if index < 2: return None
        
        df = pd.DataFrame(candles)
        ema_50 = df['close'].ewm(span=50, adjust=False).mean()
        
        # Calcular RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        c1, c2, c3 = candles[index-2], candles[index-1], candles[index]
        
        # Verificar que todas las velas son bajistas
        are_bearish = c1['close'] < c1['open'] and c2['close'] < c2['open'] and c3['close'] < c3['open']
        if not are_bearish: return None
        
        # Verificar cuerpos significativos (no deben ser dojis)
        c1_range = c1['high'] - c1['low']
        c2_range = c2['high'] - c2['low']
        c3_range = c3['high'] - c3['low']
        c1_body = abs(c1['close'] - c1['open'])
        c2_body = abs(c2['close'] - c2['open'])
        c3_body = abs(c3['close'] - c3['open'])
        
        are_strong = (c1_body > c1_range * 0.5 and 
                    c2_body > c2_range * 0.5 and 
                    c3_body > c3_range * 0.5)
        
        # Verificar que cada vela abre dentro del cuerpo de la anterior y cierra más bajo
        opens_in_body = (c2['open'] < c1['open'] and 
                        c2['open'] > c1['close'] and 
                        c3['open'] < c2['open'] and 
                        c3['open'] > c2['close'])
        
        closes_lower = c2['close'] < c1['close'] and c3['close'] < c2['close']
        
        # Filtros adicionales para M1
        is_resistance = CandlePatterns._is_resistance(candles, index-2)  # Formación inicia en resistencia
        is_uptrend = c1['open'] > ema_50.iloc[index-2]  # Inicia en tendencia alcista
        is_not_oversold = rsi.iloc[index] > 30  # No hay sobreventa extrema al final
        
        # Verificar volumen creciente (con manejo de errores)
        try:
            has_volume_confirmation = (c1['volume'] < c2['volume'] and c2['volume'] < c3['volume'])
        except (KeyError, TypeError):
            has_volume_confirmation = True  # Si no hay datos de volumen, no bloqueamos
        
        if (are_bearish and 
            are_strong and 
            opens_in_body and 
            closes_lower and
            is_resistance and 
            is_uptrend and 
            is_not_oversold and 
            has_volume_confirmation):
            return 'short'
            
        return None

    @staticmethod
    def is_three_inside_up_down(candles, index=-1):
        """Tres dentro arriba/abajo: combinación de harami seguido de confirmación"""
        if index < 20: return None
        
        if index < 2: return None
        
        df = pd.DataFrame(candles)
        ema_50 = df['close'].ewm(span=50, adjust=False).mean()
        
        # Calcular RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        c1, c2, c3 = candles[index-2], candles[index-1], candles[index]
        
        # Harami alcista + confirmación
        is_harami_up = (c1['close'] < c1['open'] and  # Primera vela bajista
                    c2['close'] > c2['open'] and   # Segunda vela alcista
                    c2['open'] > c1['close'] and   # Abre dentro del cuerpo
                    c2['close'] < c1['open'])      # Cierra dentro del cuerpo
        
        # Filtros adicionales para M1
        if (is_harami_up and 
            c3['close'] > c2['close'] and        # Tercera vela confirma tendencia alcista
            c1['close'] < ema_50.iloc[index-2] and  # Primera vela en tendencia bajista
            rsi.iloc[index-2] < 40 and           # RSI en sobreventa al inicio (relajado de 35 a 40)
            CandlePatterns._is_support(candles, index-2) and  # Patrón inicia en soporte
            CandlePatterns._check_volume_confirmation(candles, index)):  # Volumen confirmación
            return 'long'
        
        # Harami bajista + confirmación
        is_harami_down = (c1['close'] > c1['open'] and  # Primera vela alcista
                        c2['close'] < c2['open'] and   # Segunda vela bajista
                        c2['open'] < c1['close'] and   # Abre dentro del cuerpo
                        c2['close'] > c1['open'])      # Cierra dentro del cuerpo
        
        # Filtros adicionales para M1
        if (is_harami_down and 
            c3['close'] < c2['close'] and        # Tercera vela confirma tendencia bajista
            c1['close'] > ema_50.iloc[index-2] and  # Primera vela en tendencia alcista
            rsi.iloc[index-2] > 60 and           # RSI en sobrecompra al inicio (relajado de 65 a 60)
            CandlePatterns._is_resistance(candles, index-2) and  # Patrón inicia en resistencia
            CandlePatterns._check_volume_confirmation(candles, index)):  # Volumen confirmación
            return 'short'
            
        return None

    @staticmethod
    def is_three_outside_up_down(candles, index=-1):
        """Tres fuera arriba/abajo: combinación de envolvente seguido de confirmación"""
        if index < 20: return None
        
        if index < 2: return None
        
        df = pd.DataFrame(candles)
        ema_50 = df['close'].ewm(span=50, adjust=False).mean()
        
        # Calcular RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        c1, c2, c3 = candles[index-2], candles[index-1], candles[index]
        
        # Envolvente alcista + confirmación
        is_engulfing_up = (c1['close'] < c1['open'] and  # Primera vela bajista
                        c2['close'] > c2['open'] and   # Segunda vela alcista
                        c2['close'] > c1['open'] and   # Cierra por encima
                        c2['open'] < c1['close'])      # Abre por debajo
        
        # Filtros adicionales para M1
        if (is_engulfing_up and 
            c3['close'] > c2['close'] and        # Tercera vela confirma tendencia alcista
            c1['close'] < ema_50.iloc[index-2] and  # Primera vela en tendencia bajista
            rsi.iloc[index-2] < 40 and           # RSI en sobreventa al inicio (relajado de 35 a 40)
            CandlePatterns._is_support(candles, index-2) and  # Patrón inicia en soporte
            CandlePatterns._check_volume_confirmation(candles, index)):  # Volumen confirmación
            return 'long'
        
        # Envolvente bajista + confirmación
        is_engulfing_down = (c1['close'] > c1['open'] and  # Primera vela alcista
                            c2['close'] < c2['open'] and   # Segunda vela bajista
                            c2['open'] > c1['close'] and   # Abre por encima
                            c2['close'] < c1['open'])      # Cierra por debajo
        
        # Filtros adicionales para M1
        if (is_engulfing_down and 
            c3['close'] < c2['close'] and        # Tercera vela confirma tendencia bajista
            c1['close'] > ema_50.iloc[index-2] and  # Primera vela en tendencia alcista
            rsi.iloc[index-2] > 60 and           # RSI en sobrecompra al inicio (relajado de 65 a 60)
            CandlePatterns._is_resistance(candles, index-2) and  # Patrón inicia en resistencia
            CandlePatterns._check_volume_confirmation(candles, index)):  # Volumen confirmación
            return 'short'
            
        return None

    # --- Patrones de Cinco Velas ---

    @staticmethod
    def is_rising_three_methods(candles, index=-1):
        """
        Método de tres pasos alcista: Una vela alcista grande seguida de tres velas 
        bajistas pequeñas dentro del rango de la primera, y una última vela alcista 
        que cierra por encima de la primera.
        """
        if index < 20: return None
        
        # Necesitamos al menos 5 velas para este patrón
        if index < 4: return None
        
        df = pd.DataFrame(candles)
        ema_50 = df['close'].ewm(span=50, adjust=False).mean()
        
        # Calcular RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        c1, c2, c3, c4, c5 = candles[index-4:index+1]
        
        # Verificar estructura básica
        c1_bullish = c1['close'] > c1['open']  # Primera vela alcista
        c5_bullish = c5['close'] > c5['open']  # Última vela alcista
        
        # Las tres velas intermedias deben ser bajistas
        three_bearish = (c2['close'] < c2['open'] and 
                        c3['close'] < c3['open'] and 
                        c4['close'] < c4['open'])
        
        # Las velas intermedias deben estar contenidas en el rango de la primera
        contained = all(max(c['open'], c['close']) < c1['high'] and 
                    min(c['open'], c['close']) > c1['low'] for c in [c2, c3, c4])
        
        # La última vela debe cerrar por encima de la primera
        c5_closes_higher = c5['close'] > c1['close']
        
        # Filtros adicionales para M1
        is_uptrend = c1['close'] > ema_50.iloc[index-4]  # Ya en tendencia alcista
        is_not_overbought = rsi.iloc[index] < 80  # No extremadamente sobrecomprado al final
        
        # Verificar volumen (primera y última vela con mayor volumen)
        try:
            volume_pattern = (c1['volume'] > c2['volume'] and 
                            c1['volume'] > c3['volume'] and 
                            c1['volume'] > c4['volume'] and
                            c5['volume'] > c2['volume'] and
                            c5['volume'] > c3['volume'] and
                            c5['volume'] > c4['volume'])
        except (KeyError, TypeError):
            volume_pattern = True  # Si no hay datos de volumen, no bloqueamos
        
        if (c1_bullish and c5_bullish and three_bearish and 
            contained and c5_closes_higher and
            is_uptrend and is_not_overbought and volume_pattern):
            return 'long'
        
        return None

    @staticmethod
    def is_falling_three_methods(candles, index=-1):
        """
        Método de tres pasos bajista: Una vela bajista grande seguida de tres velas 
        alcistas pequeñas dentro del rango de la primera, y una última vela bajista 
        que cierra por debajo de la primera.
        """
        if index < 20: return None
        
        # Necesitamos al menos 5 velas para este patrón
        if index < 4: return None
        
        df = pd.DataFrame(candles)
        ema_50 = df['close'].ewm(span=50, adjust=False).mean()
        
        # Calcular RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        c1, c2, c3, c4, c5 = candles[index-4:index+1]
        
        # Verificar estructura básica
        c1_bearish = c1['close'] < c1['open']  # Primera vela bajista
        c5_bearish = c5['close'] < c5['open']  # Última vela bajista
        
        # Las tres velas intermedias deben ser alcistas
        three_bullish = (c2['close'] > c2['open'] and 
                        c3['close'] > c3['open'] and 
                        c4['close'] > c4['open'])
        
        # Las velas intermedias deben estar contenidas en el rango de la primera
        contained = all(max(c['open'], c['close']) < c1['high'] and 
                    min(c['open'], c['close']) > c1['low'] for c in [c2, c3, c4])
        
        # La última vela debe cerrar por debajo de la primera
        c5_closes_lower = c5['close'] < c1['close']
        
        # Filtros adicionales para M1
        is_downtrend = c1['close'] < ema_50.iloc[index-4]  # Ya en tendencia bajista
        is_not_oversold = rsi.iloc[index] > 20  # No extremadamente sobrevendido al final
        is_resistance = CandlePatterns._is_resistance(candles, index-4)  # La secuencia comienza en resistencia
        
        # Verificar volumen (primera y última vela con mayor volumen)
        try:
            volume_pattern = (c1['volume'] > c2['volume'] and 
                            c1['volume'] > c3['volume'] and 
                            c1['volume'] > c4['volume'] and
                            c5['volume'] > c2['volume'] and
                            c5['volume'] > c3['volume'] and
                            c5['volume'] > c4['volume'])
        except (KeyError, TypeError):
            volume_pattern = True  # Si no hay datos de volumen, no bloqueamos
        
        if (c1_bearish and c5_bearish and three_bullish and 
            contained and c5_closes_lower and
            is_downtrend and is_not_oversold and is_resistance and
            volume_pattern):
            return 'short'
        
        return None

    # --------------------------------------------------------------------------
    # Método Principal de Detección
    # --------------------------------------------------------------------------

    
    @staticmethod
    def detect_all_patterns(candles, index=-1):
        """Detecta todos los patrones de velas en el índice especificado"""
        all_pattern_functions = [
            CandlePatterns.is_hammer, 
            CandlePatterns.is_shooting_star, 
            CandlePatterns.is_marubozu,
            CandlePatterns.is_dragonfly_doji, 
            CandlePatterns.is_gravestone_doji, 
            CandlePatterns.is_hanging_man,
            CandlePatterns.is_inverted_hammer,
            CandlePatterns.is_morning_star,
            CandlePatterns.is_long_legged_doji,
            CandlePatterns.is_doji,
            CandlePatterns.is_doji_reversal, 
            CandlePatterns.is_engulfing, 
            CandlePatterns.is_harami, 
            CandlePatterns.is_piercing_line,
            CandlePatterns.is_dark_cloud_cover, 
            CandlePatterns.is_evening_star,
            CandlePatterns.is_three_white_soldiers, 
            CandlePatterns.is_three_black_crows,
            CandlePatterns.is_three_inside_up_down, 
            CandlePatterns.is_three_outside_up_down,
            CandlePatterns.is_falling_three_methods,
            CandlePatterns.is_rising_three_methods
        ]
        
        signals = {'long': [], 'short': [], 'neutral': []}
        for pattern_func in all_pattern_functions:
            result = pattern_func(candles, index)
            if result:
                pattern_name = pattern_func.__name__.replace('is_', '')
                if result in signals:
                    signals[result].append(pattern_name)
        return signals
