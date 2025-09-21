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
        if 'low' not in df.columns or 'high' not in df.columns: return None
        support = df['low'].iloc[-lookback:-2].min()
        resistance = df['high'].iloc[-lookback:-2].max()
        candle_data = df.to_dict('records')
        signals = CandlePatterns.detect_all_patterns(candle_data)
        
        # Aumentamos la tolerancia a 1% y añadimos más patrones de vela
        is_near_support = abs(df['low'].iloc[-1] - support) / support < 0.01
        if is_near_support and ('hammer' in signals['long'] or 'engulfing' in signals['long'] or 'doji' in signals['neutral'] or 'piercing_line' in signals['long']):
            return 'long'
        
        is_near_resistance = abs(df['high'].iloc[-1] - resistance) / resistance < 0.01
        if is_near_resistance and ('shooting_star' in signals['short'] or 'engulfing' in signals['short'] or 'doji' in signals['neutral'] or 'dark_cloud_cover' in signals['short']):
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
        if 'rsi' not in df.columns or 'macd_line' not in df.columns or 'macd_signal' not in df.columns: return None
        if df['rsi'].iloc[-1] > 50 and df['rsi'].iloc[-1] < 70 and df['macd_line'].iloc[-1] > df['macd_signal'].iloc[-1] and df['macd_line'].iloc[-2] <= df['macd_signal'].iloc[-2]:
            return 'long'
        if df['rsi'].iloc[-1] < 50 and df['rsi'].iloc[-1] > 30 and df['macd_line'].iloc[-1] < df['macd_signal'].iloc[-1] and df['macd_line'].iloc[-2] >= df['macd_signal'].iloc[-2]:
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
        required = ['close', 'ema_50', 'ema_200', 'rsi', 'macd_line']
        if not all(col in df.columns for col in required): return None
        price = df['close'].iloc[-1]
        if price > df['ema_200'].iloc[-1] and df['rsi'].iloc[-1] > 50 and df['macd_line'].iloc[-1] > 0:
            return 'long'
        if price < df['ema_200'].iloc[-1] and df['rsi'].iloc[-1] < 50 and df['macd_line'].iloc[-1] < 0:
            return 'short'
        return None

    @staticmethod
    def strategy_candle_pattern_reversal(df, lookback=50):
        support = df['low'].iloc[-lookback:-2].min()
        resistance = df['high'].iloc[-lookback:-2].max()
        candle_data = df.to_dict('records')
        signals = CandlePatterns.detect_all_patterns(candle_data)
        if abs(df['low'].iloc[-1] - support) / support < 0.01 and ('doji' in signals['neutral'] or 'hammer' in signals['long'] or 'engulfing' in signals['long']):
            return 'long'
        if abs(df['high'].iloc[-1] - resistance) / resistance < 0.01 and ('doji' in signals['neutral'] or 'shooting_star' in signals['short'] or 'engulfing' in signals['short']):
            return 'short'
        return None

    @staticmethod
    def strategy_scalping_stochrsi_ema(df):
        required = ['close', 'ema_slow', 'stochrsi_k']
        if not all(col in df.columns for col in required): return None
        price = df['close'].iloc[-1]
        if price > df['ema_slow'].iloc[-1] and df['stochrsi_k'].iloc[-1] > 20 and df['stochrsi_k'].iloc[-2] <= 20:
            return 'long'
        if price < df['ema_slow'].iloc[-1] and df['stochrsi_k'].iloc[-1] < 80 and df['stochrsi_k'].iloc[-2] >= 80:
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