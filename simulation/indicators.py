import pandas as pd

try:
    import pandas_ta as ta
except ImportError:
    ta = None
    print("pandas_ta no está instalado. Los indicadores no se calcularán.")


class IndicatorCalculator:
    """Calcula indicadores técnicos usando pandas_ta."""
    
    def __init__(self, debug_mode=False, logger=None):
        self.debug_mode = debug_mode
        self.logger = logger
    
    def _log(self, message, level='info'):
        """Helper para registrar mensajes."""
        if self.logger:
            log_methods = {
                'info': self.logger.log,
                'success': self.logger.success,
                'error': self.logger.error,
                'warn': self.logger.warn
            }
            log_methods.get(level, self.logger.log)(message)
        else:
            print(message)
    
    def calculate_all_indicators(self, candles_df):
        """
        Calcula TODOS los indicadores técnicos usando pandas_ta.
        Añade columnas al DataFrame: RSI, ATR, MACD, Momentum, EMAs, Bollinger Bands, StochRSI.
        """
        if candles_df.empty or len(candles_df) < 50:
            if self.debug_mode:
                self._log("[INDICATORS-DEBUG] No hay suficientes velas para calcular indicadores (mínimo 50)")
            return candles_df
        
        if ta is None:
            self._log("[INDICATORS-ERROR] pandas_ta no está disponible. No se pueden calcular indicadores.", 'error')
            return candles_df
        
        try:
            # Crear copia con columnas en mayúsculas (requerido por pandas_ta)
            df = candles_df.copy()
            df.columns = [col.capitalize() if col != 'time' else col for col in df.columns]
            
            # --- RSI (14) ---
            rsi = ta.rsi(df['Close'], length=14)
            candles_df['RSI'] = rsi
            
            # --- ATR (14) ---
            atr = ta.atr(df['High'], df['Low'], df['Close'], length=14)
            candles_df['ATR'] = atr
            
            # --- MACD (12, 26, 9) ---
            macd_result = ta.macd(df['Close'], fast=12, slow=26, signal=9)
            if macd_result is not None and not macd_result.empty:
                candles_df['MACD_line'] = macd_result['MACD_12_26_9']
                candles_df['MACD_signal'] = macd_result['MACDs_12_26_9']
                candles_df['MACD_histogram'] = macd_result['MACDh_12_26_9']
            
            # --- Momentum (10) ---
            momentum = ta.mom(df['Close'], length=10)
            candles_df['Momentum'] = momentum
            
            # --- StochRSI (14, 14, 3, 3) para strategy_scalping_stochrsi_ema ---
            stochrsi_result = ta.stochrsi(df['Close'], length=14, rsi_length=14, k=3, d=3)
            if stochrsi_result is not None and not stochrsi_result.empty:
                # Buscar columnas dinámicamente
                k_col = [col for col in stochrsi_result.columns if col.startswith('STOCHRSIk_')]
                d_col = [col for col in stochrsi_result.columns if col.startswith('STOCHRSId_')]
                
                if k_col and d_col:
                    candles_df['StochRSI_K'] = stochrsi_result[k_col[0]]
                    candles_df['StochRSI_D'] = stochrsi_result[d_col[0]]
                else:
                    candles_df['StochRSI_K'] = pd.Series([float('nan')] * len(candles_df))
                    candles_df['StochRSI_D'] = pd.Series([float('nan')] * len(candles_df))
            else:
                candles_df['StochRSI_K'] = pd.Series([float('nan')] * len(candles_df))
                candles_df['StochRSI_D'] = pd.Series([float('nan')] * len(candles_df))
            
            # --- EMAs para tendencia ---
            candles_df['EMA_20'] = ta.ema(df['Close'], length=20)
            candles_df['EMA_50'] = ta.ema(df['Close'], length=50)
            candles_df['EMA_200'] = ta.ema(df['Close'], length=200)
            
            # --- Bollinger Bands (20, 2) ---
            candles_df = self._calculate_bollinger_bands(df, candles_df)
            
            # --- Crear aliases para compatibilidad ---
            candles_df = self._create_aliases(candles_df)
            
            # --- EMAs adicionales para strategy_ma_crossover ---
            candles_df['ema_fast'] = ta.ema(df['Close'], length=10)
            candles_df['ema_slow'] = ta.ema(df['Close'], length=50)
            
            # --- Indicadores adicionales para máxima precisión ---
            # Williams %R para confirmación adicional
            candles_df['Williams_R'] = ta.willr(df['High'], df['Low'], df['Close'], length=14)
            
            # CCI (Commodity Channel Index) para detectar extremos
            candles_df['CCI'] = ta.cci(df['High'], df['Low'], df['Close'], length=20)
            
            # ADX para fuerza de tendencia
            adx_result = ta.adx(df['High'], df['Low'], df['Close'], length=14)
            if adx_result is not None and not adx_result.empty:
                adx_col = [col for col in adx_result.columns if col.startswith('ADX_')]
                if adx_col:
                    candles_df['ADX'] = adx_result[adx_col[0]]
            
            if self.debug_mode:
                last_row = candles_df.iloc[-1]
                
                # Formatear valores con manejo de NaN
                rsi_val = last_row.get('RSI', 'N/A')
                rsi_str = f"{rsi_val:.2f}" if not pd.isna(rsi_val) else 'N/A'
                
                atr_val = last_row.get('ATR', 'N/A')
                atr_str = f"{atr_val:.5f}" if not pd.isna(atr_val) else 'N/A'
                
                macd_val = last_row.get('MACD_line', 'N/A')
                macd_str = f"{macd_val:.5f}" if not pd.isna(macd_val) else 'N/A'
                
                self._log(
                    f"[INDICATORS-DEBUG] Indicadores calculados - "
                    f"RSI: {rsi_str}, ATR: {atr_str}, MACD: {macd_str}"
                )
                
        except Exception as e:
            self._log(f"[INDICATORS-ERROR] Error al calcular indicadores con pandas_ta: {e}", 'error')
            import traceback
            if self.debug_mode:
                self._log(f"[INDICATORS-DEBUG] Traceback: {traceback.format_exc()}", 'error')
        
        return candles_df
    
    def _calculate_bollinger_bands(self, df, candles_df):
        """Calcula Bollinger Bands con manejo robusto de errores."""
        bb = ta.bbands(df['Close'], length=20, std=2)
        if bb is not None and not bb.empty:
            # Buscar columnas con diferentes formatos posibles
            # Formato antiguo: 'BBU_20_2.0'
            # Formato nuevo: 'BBU_20_2.0_2.0'
            
            upper_col = None
            middle_col = None
            lower_col = None
            
            for col in bb.columns:
                if col.startswith('BBU_'):
                    upper_col = col
                elif col.startswith('BBM_'):
                    middle_col = col
                elif col.startswith('BBL_'):
                    lower_col = col
            
            if upper_col and middle_col and lower_col:
                candles_df['BB_upper'] = bb[upper_col]
                candles_df['BB_middle'] = bb[middle_col]
                candles_df['BB_lower'] = bb[lower_col]
                
                if self.debug_mode:
                    self._log(f"[INDICATORS-DEBUG] Bollinger Bands calculadas usando columnas: {upper_col}, {middle_col}, {lower_col}")
            else:
                # Logging de debug para identificar columnas disponibles
                if self.debug_mode:
                    self._log(f"[INDICATORS-DEBUG] Columnas de Bollinger Bands disponibles: {list(bb.columns)}")
                # Inicializar con NaN si no existen las columnas
                candles_df['BB_upper'] = pd.Series([float('nan')] * len(candles_df))
                candles_df['BB_middle'] = pd.Series([float('nan')] * len(candles_df))
                candles_df['BB_lower'] = pd.Series([float('nan')] * len(candles_df))
        else:
            # Si bb es None o está vacío, inicializar con NaN
            candles_df['BB_upper'] = pd.Series([float('nan')] * len(candles_df))
            candles_df['BB_middle'] = pd.Series([float('nan')] * len(candles_df))
            candles_df['BB_lower'] = pd.Series([float('nan')] * len(candles_df))
        
        return candles_df

    def _create_aliases(self, candles_df):
        """Crea aliases en minúsculas para compatibilidad con forex_list.py y candle_list.py."""
        candles_df['rsi'] = candles_df['RSI']
        candles_df['atr'] = candles_df['ATR']
        candles_df['ema_20'] = candles_df['EMA_20']
        candles_df['ema_50'] = candles_df['EMA_50']
        candles_df['ema_200'] = candles_df['EMA_200']
        candles_df['macd_line'] = candles_df['MACD_line']
        candles_df['macd_signal'] = candles_df['MACD_signal']
        candles_df['macd_histogram'] = candles_df['MACD_histogram']
        candles_df['momentum'] = candles_df['Momentum']
        
        # Crear aliases de Bollinger Bands solo si las columnas existen
        if 'BB_upper' in candles_df.columns:
            candles_df['bb_upper'] = candles_df['BB_upper']
            candles_df['bb_middle'] = candles_df['BB_middle']
            candles_df['bb_lower'] = candles_df['BB_lower']
        
        # Crear aliases de StochRSI
        if 'StochRSI_K' in candles_df.columns:
            candles_df['stochrsi_k'] = candles_df['StochRSI_K']
            candles_df['stochrsi_d'] = candles_df['StochRSI_D']
        
        # Crear aliases de indicadores adicionales
        if 'Williams_R' in candles_df.columns:
            candles_df['williams_r'] = candles_df['Williams_R']
        
        if 'CCI' in candles_df.columns:
            candles_df['cci'] = candles_df['CCI']
        
        if 'ADX' in candles_df.columns:
            candles_df['adx'] = candles_df['ADX']
        
        return candles_df
    
    def confirm_signal_with_indicators(self, candles_df, signal_type, strategy_name=None):
        """
        Confirma señales usando análisis inteligente de múltiples indicadores y tendencias.
        Sistema de confirmación INTELIGENTE:
        - Analiza las últimas 10 velas para determinar tendencia real
        - Requiere 3 de 6 confirmaciones (50% - más flexible)
        - RSI flexible pero efectivo
        - Confirmación de momentum en múltiples velas
        - Análisis de tendencia de precios
        - Usa TODOS los indicadores disponibles de forma inteligente
        """
        if candles_df.empty or len(candles_df) < 50:
            return False
        
        last_row = candles_df.iloc[-1]
        prev_row = candles_df.iloc[-2] if len(candles_df) > 1 else last_row
        
        # Obtener indicadores
        rsi = last_row.get('RSI')
        rsi_prev = prev_row.get('RSI')
        macd_line = last_row.get('MACD_line')
        macd_signal = last_row.get('MACD_signal')
        macd_line_prev = prev_row.get('MACD_line')
        macd_signal_prev = prev_row.get('MACD_signal')
        momentum = last_row.get('Momentum')
        momentum_prev = prev_row.get('Momentum')
        ema_20 = last_row.get('EMA_20')
        ema_50 = last_row.get('EMA_50')
        ema_200 = last_row.get('EMA_200')
        close = last_row['close']
        close_prev = prev_row['close']
        atr = last_row.get('ATR')
        williams_r = last_row.get('Williams_R')
        cci = last_row.get('CCI')
        bb_upper = last_row.get('bb_upper')
        bb_lower = last_row.get('bb_lower')
        bb_middle = last_row.get('bb_middle')
        
        # Verificar que tengamos datos válidos
        if pd.isna(rsi) or pd.isna(macd_line) or pd.isna(ema_50):
            if self.debug_mode:
                self._log(f"[INDICATORS-DEBUG] Indicadores críticos no disponibles para confirmación")
            return False
        
        # --- ANÁLISIS DE TENDENCIA DE LAS ÚLTIMAS 10 VELAS ---
        def analyze_trend_last_candles(df, periods=10):
            """Analiza la tendencia real de las últimas N velas."""
            if len(df) < periods:
                return 'neutral'
            
            recent_candles = df.iloc[-periods:]
            closes = recent_candles['close']
            
            # Contar velas alcistas vs bajistas
            bullish_candles = sum(recent_candles['close'] > recent_candles['open'])
            bearish_candles = sum(recent_candles['close'] < recent_candles['open'])
            
            # Tendencia del precio (primer vs último cierre)
            price_change = (closes.iloc[-1] - closes.iloc[0]) / closes.iloc[0]
            
            # Momentum promedio
            if 'Momentum' in df.columns:
                avg_momentum = recent_candles['Momentum'].mean()
            else:
                avg_momentum = 0
            
            # Determinar tendencia
            if bullish_candles > bearish_candles * 1.3 and price_change > 0.001:
                return 'bullish'
            elif bearish_candles > bullish_candles * 1.3 and price_change < -0.001:
                return 'bearish'
            else:
                return 'neutral'
        
        market_trend = analyze_trend_last_candles(candles_df, periods=10)
        
        # --- ANÁLISIS DE MOMENTUM EN MÚLTIPLES VELAS ---
        def check_momentum_consistency(df, direction, periods=5):
            """Verifica consistencia del momentum en las últimas N velas."""
            if len(df) < periods or 'Momentum' not in df.columns:
                return False
            
            recent_momentum = df['Momentum'].iloc[-periods:]
            
            if direction == 'bullish':
                # Al menos 60% de las velas con momentum positivo
                positive_count = sum(recent_momentum > 0)
                return positive_count >= (periods * 0.6)
            else:
                # Al menos 60% de las velas con momentum negativo
                negative_count = sum(recent_momentum < 0)
                return negative_count >= (periods * 0.6)
        
        momentum_bullish_consistent = check_momentum_consistency(candles_df, 'bullish', 5)
        momentum_bearish_consistent = check_momentum_consistency(candles_df, 'bearish', 5)
        
        # CONFIRMACIÓN PARA LONG
        if signal_type == 'long':
            # 1. RSI: Flexible pero efectivo (no sobrecomprado, preferible en zona baja-media)
            rsi_favorable = rsi < 65 and rsi > rsi_prev and rsi > 30
            rsi_ok = rsi_favorable
            
            # 2. MACD: Cruce alcista O posición alcista con momentum
            macd_cross_up = (macd_line > macd_signal and macd_line_prev <= macd_signal_prev)
            macd_bullish_position = macd_line > macd_signal and macd_line > macd_line_prev
            macd_ok = macd_cross_up or macd_bullish_position
            
            # 3. Momentum: Positivo o mejorando consistentemente
            momentum_improving = momentum > momentum_prev if not pd.isna(momentum_prev) else True
            momentum_ok = (momentum > 0 or momentum_improving) and momentum_bullish_consistent
            
            # 4. Precio: Análisis de posición respecto a medias móviles
            price_above_ema20 = close > ema_20 if not pd.isna(ema_20) else True
            price_near_ema50 = abs(close - ema_50) / ema_50 < 0.01 if not pd.isna(ema_50) else False  # Cerca de EMA50
            price_momentum = close > close_prev
            price_ok = (price_above_ema20 or price_near_ema50) and price_momentum
            
            # 5. Tendencia del mercado: Alcista o neutral + precio sobre EMA_200
            trend_favorable = market_trend in ['bullish', 'neutral']
            price_vs_ema200 = close > ema_200 * 0.995 if not pd.isna(ema_200) else True
            trend_ok = trend_favorable and price_vs_ema200
            
            # 6. Confirmación adicional con múltiples indicadores
            additional_ok = False
            confirmations_count = 0
            
            # Williams %R favorable (saliendo de sobreventa)
            if not pd.isna(williams_r) and williams_r > -80 and williams_r < -30:
                confirmations_count += 1
            
            # CCI favorable (no extremo negativo)
            if not pd.isna(cci) and cci > -100:
                confirmations_count += 1
            
            # Bollinger Bands: cerca de banda inferior o en zona media-baja
            if not pd.isna(bb_lower) and not pd.isna(bb_upper):
                bb_position = (close - bb_lower) / (bb_upper - bb_lower)
                if bb_position < 0.5:  # En mitad inferior
                    confirmations_count += 1
            
            # ATR: volatilidad razonable (no extrema)
            if not pd.isna(atr):
                atr_ratio = atr / close
                if 0.0005 < atr_ratio < 0.005:  # Volatilidad normal
                    confirmations_count += 1
            
            additional_ok = confirmations_count >= 2  # Al menos 2 de 4 confirmaciones adicionales
            
            confirmations = [rsi_ok, macd_ok, momentum_ok, price_ok, trend_ok, additional_ok]
            confirmed_count = sum(confirmations)
            
            if self.debug_mode:
                self._log(
                    f"[INDICATORS-DEBUG] Confirmación LONG INTELIGENTE para '{strategy_name}':\n"
                    f"  RSI={rsi_ok} (RSI={rsi:.1f}, prev={rsi_prev:.1f})\n"
                    f"  MACD={macd_ok} (cross_up={macd_cross_up}, bullish={macd_bullish_position})\n"
                    f"  Momentum={momentum_ok} (actual={momentum:.2f}, consistente={momentum_bullish_consistent})\n"
                    f"  Precio={price_ok} (close={close:.5f}, prev={close_prev:.5f})\n"
                    f"  Tendencia={trend_ok} (mercado={market_trend}, vs_EMA200={price_vs_ema200})\n"
                    f"  Adicional={additional_ok} ({confirmations_count}/4 confirmaciones)\n"
                    f"  Total: {confirmed_count}/6 (requiere ≥3 para confirmar)"
                )
            
            # Requiere al menos 3 de 6 confirmaciones (50% - más flexible pero inteligente)
            return confirmed_count >= 3
        
        # CONFIRMACIÓN PARA SHORT
        elif signal_type == 'short':
            # 1. RSI: Flexible pero efectivo (no sobrevendido, preferible en zona alta-media)
            rsi_favorable = rsi > 35 and rsi < rsi_prev and rsi < 70
            rsi_ok = rsi_favorable
            
            # 2. MACD: Cruce bajista O posición bajista con momentum
            macd_cross_down = (macd_line < macd_signal and macd_line_prev >= macd_signal_prev)
            macd_bearish_position = macd_line < macd_signal and macd_line < macd_line_prev
            macd_ok = macd_cross_down or macd_bearish_position
            
            # 3. Momentum: Negativo o empeorando consistentemente
            momentum_worsening = momentum < momentum_prev if not pd.isna(momentum_prev) else True
            momentum_ok = (momentum < 0 or momentum_worsening) and momentum_bearish_consistent
            
            # 4. Precio: Análisis de posición respecto a medias móviles
            price_below_ema20 = close < ema_20 if not pd.isna(ema_20) else True
            price_near_ema50 = abs(close - ema_50) / ema_50 < 0.01 if not pd.isna(ema_50) else False
            price_momentum = close < close_prev
            price_ok = (price_below_ema20 or price_near_ema50) and price_momentum
            
            # 5. Tendencia del mercado: Bajista o neutral + precio bajo EMA_200
            trend_favorable = market_trend in ['bearish', 'neutral']
            price_vs_ema200 = close < ema_200 * 1.005 if not pd.isna(ema_200) else True
            trend_ok = trend_favorable and price_vs_ema200
            
            # 6. Confirmación adicional con múltiples indicadores
            additional_ok = False
            confirmations_count = 0
            
            # Williams %R favorable (saliendo de sobrecompra)
            if not pd.isna(williams_r) and williams_r < -20 and williams_r > -70:
                confirmations_count += 1
            
            # CCI favorable (no extremo positivo)
            if not pd.isna(cci) and cci < 100:
                confirmations_count += 1
            
            # Bollinger Bands: cerca de banda superior o en zona media-alta
            if not pd.isna(bb_lower) and not pd.isna(bb_upper):
                bb_position = (close - bb_lower) / (bb_upper - bb_lower)
                if bb_position > 0.5:  # En mitad superior
                    confirmations_count += 1
            
            # ATR: volatilidad razonable (no extrema)
            if not pd.isna(atr):
                atr_ratio = atr / close
                if 0.0005 < atr_ratio < 0.005:  # Volatilidad normal
                    confirmations_count += 1
            
            additional_ok = confirmations_count >= 2  # Al menos 2 de 4 confirmaciones adicionales
            
            confirmations = [rsi_ok, macd_ok, momentum_ok, price_ok, trend_ok, additional_ok]
            confirmed_count = sum(confirmations)
            
            if self.debug_mode:
                self._log(
                    f"[INDICATORS-DEBUG] Confirmación SHORT INTELIGENTE para '{strategy_name}':\n"
                    f"  RSI={rsi_ok} (RSI={rsi:.1f}, prev={rsi_prev:.1f})\n"
                    f"  MACD={macd_ok} (cross_down={macd_cross_down}, bearish={macd_bearish_position})\n"
                    f"  Momentum={momentum_ok} (actual={momentum:.2f}, consistente={momentum_bearish_consistent})\n"
                    f"  Precio={price_ok} (close={close:.5f}, prev={close_prev:.5f})\n"
                    f"  Tendencia={trend_ok} (mercado={market_trend}, vs_EMA200={price_vs_ema200})\n"
                    f"  Adicional={additional_ok} ({confirmations_count}/4 confirmaciones)\n"
                    f"  Total: {confirmed_count}/6 (requiere ≥3 para confirmar)"
                )
            
            # Requiere al menos 3 de 6 confirmaciones (50% - más flexible pero inteligente)
            return confirmed_count >= 3
        
        return False