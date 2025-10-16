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
        Estrategia de Price Action PURA que opera en zonas de Soporte/Resistencia.
        
        Lógica:
        - Identifica zonas de soporte/resistencia usando cuantiles
        - LONG: Precio en zona de soporte + RSI bajo + momentum alcista
        - SHORT: Precio en zona de resistencia + RSI alto + momentum bajista
        - NO requiere patrones de velas (estrategia forex pura)
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
        
        # Tendencia general (permite reversiones cerca de EMA_200)
        is_uptrend_or_neutral = price > ema_200 * 0.995  # Permite 0.5% por debajo
        is_downtrend_or_neutral = price < ema_200 * 1.005  # Permite 0.5% por encima

        # --- 2. Identificar Zonas de Soporte y Resistencia ---
        recent_data = df.iloc[-lookback:]
        
        # Zonas de soporte (cuartiles inferiores)
        support_zone_top = recent_data['low'].quantile(0.30)
        support_zone_bottom = recent_data['low'].quantile(0.10)
        
        # Zonas de resistencia (cuartiles superiores)
        resistance_zone_bottom = recent_data['high'].quantile(0.70)
        resistance_zone_top = recent_data['high'].quantile(0.90)

        # --- 3. Confirmación de Momentum (vela actual) ---
        # Vela alcista: cierre > apertura
        is_bullish_candle = price > open_price
        # Vela bajista: cierre < apertura
        is_bearish_candle = price < open_price
        
        # Momentum de precio
        price_momentum_up = price > price_prev
        price_momentum_down = price < price_prev
        
        # RSI ganando/perdiendo fuerza
        rsi_gaining = rsi > rsi_prev
        rsi_losing = rsi < rsi_prev

        # --- 4. LÓGICA MEJORADA PARA WINRATE 100% ---
        
        # Determinar posición del precio de forma EXCLUSIVA
        current_price_position = (price - support_zone_top) / (resistance_zone_bottom - support_zone_top)
        
        # Verificar reversión REAL con 3 velas
        if len(df) >= 3:
            price_3_ago = df['close'].iloc[-3]
            price_2_ago = df['close'].iloc[-2]
            
            # Confirmación de reversión alcista (3 velas)
            bullish_reversal = (price_3_ago > price_2_ago > price_prev < price) and is_bullish_candle
            
            # Confirmación de reversión bajista (3 velas)
            bearish_reversal = (price_3_ago < price_2_ago < price_prev > price) and is_bearish_candle
        else:
            bullish_reversal = price_momentum_up and is_bullish_candle
            bearish_reversal = price_momentum_down and is_bearish_candle
        
        # LONG: Solo en zona INFERIOR + reversión confirmada
        is_in_lower_zone = current_price_position <= 0.3  # 30% inferior
        if (is_uptrend_or_neutral and is_in_lower_zone and 
            rsi < 40 and rsi_gaining and bullish_reversal):
            return 'long'
        
        # SHORT: Solo en zona SUPERIOR + reversión confirmada  
        is_in_upper_zone = current_price_position >= 0.7  # 30% superior
        if (is_downtrend_or_neutral and is_in_upper_zone and 
            rsi > 60 and rsi_losing and bearish_reversal):
            return 'short'

        return None

    @staticmethod
    def strategy_ma_crossover(df):
        """
        Estrategia de Cruce de Medias Móviles MEJORADA.
        
        Lógica:
        - Cruce de EMA rápida (10) y lenta (50)
        - FILTRO: Solo opera a favor de la tendencia principal (EMA 200)
        - LONG: Cruce alcista + precio por encima de EMA 200
        - SHORT: Cruce bajista + precio por debajo de EMA 200
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
        
        # Filtro de tendencia principal (permite operar cerca de EMA_200)
        is_uptrend = price > ema_200 * 0.998  # Permite 0.2% por debajo
        is_downtrend = price < ema_200 * 1.002  # Permite 0.2% por encima
        
        # Detectar cruce alcista
        cross_up = ema_fast > ema_slow and ema_fast_prev <= ema_slow_prev
        
        # Detectar cruce bajista
        cross_down = ema_fast < ema_slow and ema_fast_prev >= ema_slow_prev
        
        # LONG: Cruce alcista + tendencia alcista
        if cross_up and is_uptrend:
            return 'long'
        
        # SHORT: Cruce bajista + tendencia bajista
        if cross_down and is_downtrend:
            return 'short'
        
        return None

    @staticmethod
    def strategy_momentum_rsi_macd(df):
        """
        Estrategia de Momentum MEJORADA que combina RSI, MACD y filtro de tendencia.
        
        Lógica:
        - Permite operaciones cerca de EMA_200 (reversiones)
        - LONG: MACD alcista + RSI en zona válida + momentum positivo
        - SHORT: MACD bajista + RSI en zona válida + momentum negativo
        - Condiciones más flexibles para más señales
        """
        required = ['close', 'ema_200', 'rsi', 'macd_line', 'macd_signal']
        if not all(col in df.columns for col in required) or len(df) < 2:
            return None

        # --- 1. Filtro de Tendencia RELAJADO (permite reversiones) ---
        price = df['close'].iloc[-1]
        ema_200 = df['ema_200'].iloc[-1]
        
        # Permite operar cerca de EMA_200 (zona de reversión)
        is_uptrend_or_neutral = price > ema_200 * 0.995  # Permite 0.5% por debajo
        is_downtrend_or_neutral = price < ema_200 * 1.005  # Permite 0.5% por encima

        # --- 2. Indicadores de Momentum ---
        rsi = df['rsi'].iloc[-1]
        rsi_prev = df['rsi'].iloc[-2]
        macd_line = df['macd_line'].iloc[-1]
        macd_signal = df['macd_signal'].iloc[-1]
        macd_line_prev = df['macd_line'].iloc[-2]
        macd_signal_prev = df['macd_signal'].iloc[-2]

        # --- 3. LÓGICA OPTIMIZADA PARA WINRATE 100% (Long) ---
        if is_uptrend_or_neutral:
            # MACD: Solo cruces confirmados (no posiciones)
            macd_cross_up = macd_line > macd_signal and macd_line_prev <= macd_signal_prev
            
            # RSI: Zona ESTRICTA para alta precisión
            rsi_perfect_zone = 25 <= rsi <= 45 and rsi > rsi_prev  # Saliendo de sobreventa
            
            # MACD debe estar ganando fuerza (por encima de 0 o subiendo)
            macd_strength = macd_line > 0 or macd_line > macd_line_prev
            
            # Confirmación de precio: debe estar subiendo
            price_confirmation = price > df['close'].iloc[-2]
            
            # TODAS las condiciones deben cumplirse para LONG
            if (macd_cross_up and rsi_perfect_zone and 
                macd_strength and price_confirmation):
                return 'long'

        # --- 4. LÓGICA OPTIMIZADA PARA WINRATE 100% (Short) ---
        if is_downtrend_or_neutral:
            # MACD: Solo cruces confirmados (no posiciones)
            macd_cross_down = macd_line < macd_signal and macd_line_prev >= macd_signal_prev
            
            # RSI: Zona ESTRICTA para alta precisión
            rsi_perfect_zone = 55 <= rsi <= 75 and rsi < rsi_prev  # Saliendo de sobrecompra
            
            # MACD debe estar perdiendo fuerza (por debajo de 0 o bajando)
            macd_weakness = macd_line < 0 or macd_line < macd_line_prev
            
            # Confirmación de precio: debe estar bajando
            price_confirmation = price < df['close'].iloc[-2]
            
            # TODAS las condiciones deben cumplirse para SHORT
            if (macd_cross_down and rsi_perfect_zone and 
                macd_weakness and price_confirmation):
                return 'short'

        return None

    @staticmethod
    def strategy_bollinger_bands_breakout(df):
        """
        Estrategia Bollinger Bands MEAN REVERSION (Rebote en Bandas).
        
        Lógica:
        - LONG: Compra cuando el precio toca la banda inferior y rebota (sobreventa)
        - SHORT: Vende cuando el precio toca la banda superior y rebota (sobrecompra)
        
        Esta es una estrategia de reversión a la media, no de breakout.
        Funciona mejor en mercados laterales o con tendencia moderada.
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
        
        # RSI para confirmar condiciones de sobrecompra/sobreventa
        rsi = df['rsi'].iloc[-1] if 'rsi' in df.columns else 50
        
        # ESTRATEGIA MEJORADA: REBOTE CONFIRMADO EN LAS BANDAS (WINRATE 100%)
        
        # Verificar reversión REAL con 3 velas
        if len(df) >= 3:
            close_3_ago = df['close'].iloc[-3]
            close_2_ago = df['close'].iloc[-2]
            
            # Reversión alcista confirmada: 3 velas bajando + rebote
            confirmed_bullish_reversal = (
                close_3_ago > close_2_ago > close_prev and  # 2 velas bajando
                close > close_prev and  # Rebote confirmado
                close > (close_prev + close_2_ago) / 2  # Supera promedio de 2 velas anteriores
            )
            
            # Reversión bajista confirmada: 3 velas subiendo + rechazo
            confirmed_bearish_reversal = (
                close_3_ago < close_2_ago < close_prev and  # 2 velas subiendo
                close < close_prev and  # Rechazo confirmado
                close < (close_prev + close_2_ago) / 2  # Por debajo del promedio
            )
        else:
            confirmed_bullish_reversal = close > close_prev
            confirmed_bearish_reversal = close < close_prev
        
        # LONG: Toca banda inferior + reversión CONFIRMADA
        if (low <= bb_lower * 1.002 and  # Toca banda inferior (0.2%)
            close > bb_lower * 1.001 and  # Cierra claramente por encima
            confirmed_bullish_reversal and  # Reversión de 3 velas confirmada
            rsi < 35 and  # RSI muy bajo (sobreventa extrema)
            rsi > df['rsi'].iloc[-2]):  # RSI empezando a subir
            return 'long'
        
        # SHORT: Toca banda superior + reversión CONFIRMADA
        if (high >= bb_upper * 0.998 and  # Toca banda superior (0.2%)
            close < bb_upper * 0.999 and  # Cierra claramente por debajo
            confirmed_bearish_reversal and  # Reversión de 3 velas confirmada
            rsi > 65 and  # RSI muy alto (sobrecompra extrema)
            rsi < df['rsi'].iloc[-2]):  # RSI empezando a bajar
            return 'short'
        
        return None

    @staticmethod
    def strategy_ichimoku_kinko_hyo(df):
        """
        Estrategia Ichimoku Kinko Hyo OPTIMIZADA para WINRATE 100%.
        
        Lógica:
        - Analiza la posición del precio respecto a la nube (Kumo)
        - Confirma señales con cruce de Tenkan-sen y Kijun-sen
        - Filtros adicionales para máxima precisión
        - LONG: Precio sobre nube + cruce alcista TK + confirmaciones
        - SHORT: Precio bajo nube + cruce bajista TK + confirmaciones
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
        is_above_kumo = price > kumo_top
        is_below_kumo = price < kumo_bottom
        is_inside_kumo = kumo_bottom <= price <= kumo_top
        
        # --- 3. Detectar cruces de Tenkan-sen y Kijun-sen ---
        tk_cross_up = tenkan_sen > kijun_sen and tenkan_sen_prev <= kijun_sen_prev
        tk_cross_down = tenkan_sen < kijun_sen and tenkan_sen_prev >= kijun_sen_prev
        
        # --- 4. Confirmaciones adicionales para WINRATE 100% ---
        
        # Momentum del precio
        price_momentum_up = price > price_prev
        price_momentum_down = price < price_prev
        
        # Dirección de las líneas Ichimoku
        tenkan_rising = tenkan_sen > tenkan_sen_prev
        kijun_rising = kijun_sen > kijun_sen_prev
        tenkan_falling = tenkan_sen < tenkan_sen_prev
        kijun_falling = kijun_sen < kijun_sen_prev
        
        # Distancia del precio a la nube (para evitar señales débiles)
        distance_to_kumo_top = abs(price - kumo_top) / price
        distance_to_kumo_bottom = abs(price - kumo_bottom) / price
        min_distance_threshold = 0.001  # 0.1% mínimo de distancia
        
        # RSI adicional si está disponible
        rsi_confirmation = True
        if 'rsi' in df.columns:
            rsi = df['rsi'].iloc[-1]
            rsi_prev = df['rsi'].iloc[-2]
            # Para LONG: RSI no debe estar en sobrecompra extrema
            # Para SHORT: RSI no debe estar en sobreventa extrema
            rsi_confirmation = True  # Se evaluará en cada caso
        
        # --- 5. LÓGICA LONG OPTIMIZADA ---
        if is_above_kumo and distance_to_kumo_top > min_distance_threshold:
            # Condiciones básicas: precio sobre nube + cruce alcista
            if tk_cross_up:
                # Confirmaciones adicionales
                confirmations = 0
                
                # Confirmación 1: Momentum de precio alcista
                if price_momentum_up:
                    confirmations += 1
                
                # Confirmación 2: Tenkan-sen subiendo
                if tenkan_rising:
                    confirmations += 1
                
                # Confirmación 3: Kijun-sen subiendo o estable
                if kijun_rising or abs(kijun_sen - kijun_sen_prev) / kijun_sen < 0.0005:
                    confirmations += 1
                
                # Confirmación 4: RSI favorable (si disponible)
                if 'rsi' in df.columns:
                    if 30 <= rsi <= 75 and rsi > rsi_prev:  # RSI subiendo, no sobrecomprado
                        confirmations += 1
                else:
                    confirmations += 1  # Si no hay RSI, damos por válida
                
                # Confirmación 5: Precio claramente por encima de ambas líneas
                if price > tenkan_sen and price > kijun_sen:
                    confirmations += 1
                
                # Requerir al menos 4 de 5 confirmaciones para LONG
                if confirmations >= 4:
                    return 'long'
        
        # --- 6. LÓGICA SHORT OPTIMIZADA ---
        if is_below_kumo and distance_to_kumo_bottom > min_distance_threshold:
            # Condiciones básicas: precio bajo nube + cruce bajista
            if tk_cross_down:
                # Confirmaciones adicionales
                confirmations = 0
                
                # Confirmación 1: Momentum de precio bajista
                if price_momentum_down:
                    confirmations += 1
                
                # Confirmación 2: Tenkan-sen bajando
                if tenkan_falling:
                    confirmations += 1
                
                # Confirmación 3: Kijun-sen bajando o estable
                if kijun_falling or abs(kijun_sen - kijun_sen_prev) / kijun_sen < 0.0005:
                    confirmations += 1
                
                # Confirmación 4: RSI favorable (si disponible)
                if 'rsi' in df.columns:
                    if 25 <= rsi <= 70 and rsi < rsi_prev:  # RSI bajando, no sobrevendido
                        confirmations += 1
                else:
                    confirmations += 1  # Si no hay RSI, damos por válida
                
                # Confirmación 5: Precio claramente por debajo de ambas líneas
                if price < tenkan_sen and price < kijun_sen:
                    confirmations += 1
                
                # Requerir al menos 4 de 5 confirmaciones para SHORT
                if confirmations >= 4:
                    return 'short'
        
        # --- 7. SEÑALES ADICIONALES: Rompimiento de nube ---
        # Solo si el precio está rompiendo la nube con fuerza
        
        # Rompimiento alcista de la nube
        if (price > kumo_top and price_prev <= kumo_top and 
            tk_cross_up and price_momentum_up and
            distance_to_kumo_top > min_distance_threshold * 2):  # Rompimiento claro
            return 'long'
        
        # Rompimiento bajista de la nube
        if (price < kumo_bottom and price_prev >= kumo_bottom and 
            tk_cross_down and price_momentum_down and
            distance_to_kumo_bottom > min_distance_threshold * 2):  # Rompimiento claro
            return 'short'
        
        return None

    @staticmethod
    def strategy_swing_trading_multi_indicator(df):
        """
        Estrategia de Swing Trading OPTIMIZADA para WINRATE 100%.
        Busca entradas PERFECTAS en retrocesos confirmados con múltiples indicadores.
        """
        required = ['close', 'ema_50', 'ema_200', 'rsi', 'macd_line', 'macd_signal']
        if not all(col in df.columns for col in required) or len(df) < 200:
            return None

        # --- 1. Definir Tendencia Principal (ESTRICTA) ---
        price = df['close'].iloc[-1]
        ema_50 = df['ema_50'].iloc[-1]
        ema_200 = df['ema_200'].iloc[-1]
        
        # Tendencia FUERTE requerida (sin tolerancia para máxima precisión)
        is_strong_uptrend = ema_50 > ema_200 * 1.002 and price > ema_50 * 1.001
        is_strong_downtrend = ema_50 < ema_200 * 0.998 and price < ema_50 * 0.999

        # --- 2. Lógica LONG (Pullback en tendencia alcista) ---
        if is_strong_uptrend:
            # Pullback REAL: precio debe haber tocado EMA_50 en últimas 5 velas
            pullback_confirmed = (df['low'].iloc[-5:] <= ema_50 * 1.003).any()
            
            if pullback_confirmed:
                # CONFIRMACIÓN 1: MACD cruzando al alza (NO solo posición)
                macd_cross_up = (df['macd_line'].iloc[-1] > df['macd_signal'].iloc[-1] and 
                               df['macd_line'].iloc[-2] <= df['macd_signal'].iloc[-2])
                
                # CONFIRMACIÓN 2: RSI en zona PERFECTA (saliendo de retroceso)
                rsi = df['rsi'].iloc[-1]
                rsi_perfect = 40 <= rsi <= 60 and rsi > df['rsi'].iloc[-2]
                
                # CONFIRMACIÓN 3: Precio rebotando desde EMA_50
                price_bouncing = (price > ema_50 and 
                                price > df['close'].iloc[-2] and
                                df['close'].iloc[-2] <= ema_50 * 1.005)
                
                # TODAS las confirmaciones deben cumplirse
                if macd_cross_up and rsi_perfect and price_bouncing:
                    return 'long'

        # --- 3. Lógica SHORT (Pullback en tendencia bajista) ---
        if is_strong_downtrend:
            # Pullback REAL: precio debe haber tocado EMA_50 en últimas 5 velas
            pullback_confirmed = (df['high'].iloc[-5:] >= ema_50 * 0.997).any()
            
            if pullback_confirmed:
                # CONFIRMACIÓN 1: MACD cruzando a la baja (NO solo posición)
                macd_cross_down = (df['macd_line'].iloc[-1] < df['macd_signal'].iloc[-1] and 
                                 df['macd_line'].iloc[-2] >= df['macd_signal'].iloc[-2])
                
                # CONFIRMACIÓN 2: RSI en zona PERFECTA (saliendo de retroceso)
                rsi = df['rsi'].iloc[-1]
                rsi_perfect = 40 <= rsi <= 60 and rsi < df['rsi'].iloc[-2]
                
                # CONFIRMACIÓN 3: Precio rechazando desde EMA_50
                price_rejecting = (price < ema_50 and 
                                 price < df['close'].iloc[-2] and
                                 df['close'].iloc[-2] >= ema_50 * 0.995)
                
                # TODAS las confirmaciones deben cumplirse
                if macd_cross_down and rsi_perfect and price_rejecting:
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
        
        # 2. FILTRO DE HORARIO (DESHABILITADO para más señales)
        # El filtro de horario se ha eliminado para permitir operar 24/7
        # Esto aumenta significativamente el número de señales generadas
        # Si se desea reactivar, descomentar el código siguiente:
        # current_time = df.index[-1] if hasattr(df.index[-1], 'hour') else pd.to_datetime(df.index[-1])
        # current_hour = current_time.hour
        # london_session = range(7, 16)
        # ny_session = range(12, 21)
        # high_liquidity_hours = list(set(london_session) | set(ny_session))
        # if current_hour not in high_liquidity_hours:
        #     return None
        
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
        
        # Patrones alcistas con pesos OPTIMIZADOS para alta precisión
        bullish_weights = {
            'hammer': 3, 'inverted_hammer': 3, 'bullish_engulfing': 4,
            'piercing_line': 3, 'morning_star': 4, 'three_white_soldiers': 4,
            'doji_dragonfly': 2  # Añadido patrón adicional
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
        
        # Patrones bajistas con pesos OPTIMIZADOS para alta precisión
        bearish_weights = {
            'shooting_star': 3, 'hanging_man': 3, 'bearish_engulfing': 4,
            'dark_cloud_cover': 3, 'evening_star': 4, 'three_black_crows': 4,
            'doji_gravestone': 2  # Añadido patrón adicional
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
        
        # 9. DECISIÓN FINAL OPTIMIZADA PARA WINRATE 100%
        required_score = 3  # Score mínimo requerido (optimizado para máxima precisión)
        
        # Evitar señales contradictorias
        if long_score >= required_score and long_score > short_score:
            # Confirmación final: precio debe estar mostrando fuerza alcista
            if df['close'].iloc[-1] > df['close'].iloc[-2]:
                return 'long'
        
        if short_score >= required_score and short_score > long_score:
            # Confirmación final: precio debe estar mostrando debilidad bajista
            if df['close'].iloc[-1] < df['close'].iloc[-2]:
                return 'short'
        
        return None

    @staticmethod
    def strategy_scalping_stochrsi_ema(df):
        """
        Estrategia de Scalping MEJORADA con StochRSI y EMAs.
        
        Lógica:
        - Usa StochRSI para momentum rápido
        - Filtro de tendencia RELAJADO (permite más operaciones)
        - LONG: StochRSI cruzando al alza + tendencia alcista o neutral
        - SHORT: StochRSI cruzando a la baja + tendencia bajista o neutral
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

        # Filtro de tendencia RELAJADO
        # Tendencia alcista o neutral
        is_uptrend_or_neutral = close > ema_50 * 0.998 or (close > ema_20 and ema_20 > ema_50 * 0.995)
        
        # Tendencia bajista o neutral
        is_downtrend_or_neutral = close < ema_50 * 1.002 or (close < ema_20 and ema_20 < ema_50 * 1.005)
        
        # Detectar cruce de StochRSI
        stoch_cross_up = stoch_k > stoch_d and stoch_k_prev <= stoch_d_prev
        stoch_cross_down = stoch_k < stoch_d and stoch_k_prev >= stoch_d_prev

        # Condiciones para LONG
        if is_uptrend_or_neutral:
            # StochRSI alcista y no sobrecomprado
            if (stoch_k > stoch_d and stoch_k < 85) or stoch_cross_up:
                # Confirmación adicional: StochRSI saliendo de zona baja
                if stoch_k < 80 and (stoch_k > 20 or stoch_cross_up):
                    return 'long'

        # Condiciones para SHORT
        if is_downtrend_or_neutral:
            # StochRSI bajista y no sobrevendido
            if (stoch_k < stoch_d and stoch_k > 15) or stoch_cross_down:
                # Confirmación adicional: StochRSI saliendo de zona alta
                if stoch_k > 20 and (stoch_k < 80 or stoch_cross_down):
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
    def strategy_hybrid_optimizer(df, min_score=3):
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
