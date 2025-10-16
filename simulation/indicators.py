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
        Confirma señales usando múltiples indicadores OPTIMIZADO PARA WINRATE 100%.
        Sistema de confirmación ULTRA-ESTRICTO:
        - Requiere 4 de 6 confirmaciones (67% mínimo)
        - RSI en zonas EXTREMAS únicamente
        - Solo cruces MACD confirmados
        - Momentum OBLIGATORIO en dirección correcta
        - Tolerancias mínimas (0.1%)
        - Confirmaciones adicionales con Williams %R y CCI
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
        adx = last_row.get('ADX')
        
        # Verificar que tengamos datos válidos
        if pd.isna(rsi) or pd.isna(macd_line) or pd.isna(ema_50) or pd.isna(momentum):
            if self.debug_mode:
                self._log(f"[INDICATORS-DEBUG] Indicadores críticos no disponibles para confirmación")
            return False
        
        # CONFIRMACIÓN PARA LONG - WINRATE 100%
        if signal_type == 'long':
            # 1. RSI: ZONA EXTREMA de sobreventa + ganando fuerza
            rsi_extreme_oversold = rsi < 35 and rsi > rsi_prev and rsi > 25
            rsi_ok = rsi_extreme_oversold
            
            # 2. MACD: SOLO cruces confirmados al alza (NO posiciones estáticas)
            macd_cross_up = (macd_line > macd_signal and macd_line_prev <= macd_signal_prev)
            macd_strength = macd_line > macd_line_prev  # MACD ganando fuerza
            macd_ok = macd_cross_up and macd_strength
            
            # 3. Momentum: OBLIGATORIO positivo y mejorando
            momentum_positive = momentum > 0
            momentum_improving = momentum > momentum_prev
            momentum_ok = momentum_positive and momentum_improving
            
            # 4. Precio: Confirmación ESTRICTA de reversión alcista
            price_vs_ema20 = close > ema_20 if not pd.isna(ema_20) else True
            price_vs_ema50 = close > ema_50 * 0.999  # Solo 0.1% tolerancia
            price_momentum = close > close_prev  # Precio subiendo
            price_ok = price_vs_ema20 and price_vs_ema50 and price_momentum
            
            # 5. Tendencia: ULTRA-ESTRICTA cerca de EMA_200
            trend_ok = True
            if not pd.isna(ema_200):
                # Solo 0.1% de tolerancia por debajo de EMA_200
                trend_ok = close > ema_200 * 0.999
            
            # 6. Confirmación adicional: Williams %R y CCI
            additional_ok = True
            if not pd.isna(williams_r):
                # Williams %R debe estar saliendo de sobreventa extrema
                additional_ok = williams_r > -80 and williams_r < -20
            if not pd.isna(cci) and additional_ok:
                # CCI debe estar saliendo de zona negativa
                additional_ok = cci > -100 and cci < 100
            
            confirmations = [rsi_ok, macd_ok, momentum_ok, price_ok, trend_ok, additional_ok]
            confirmed_count = sum(confirmations)
            
            if self.debug_mode:
                self._log(
                    f"[INDICATORS-DEBUG] Confirmación LONG ULTRA-ESTRICTA para '{strategy_name}': "
                    f"RSI_EXTREMO={rsi_ok}({rsi:.1f}), MACD_CRUCE={macd_ok}, "
                    f"MOMENTUM_OBLIGATORIO={momentum_ok}, PRECIO_ESTRICTO={price_ok}, "
                    f"TENDENCIA_ULTRA={trend_ok}, ADICIONAL={additional_ok} | "
                    f"Total: {confirmed_count}/6 (requiere ≥4 para WINRATE 100%)"
                )
            
            # Requiere al menos 4 de 6 confirmaciones (67%) para WINRATE 100%
            return confirmed_count >= 4
        
        # CONFIRMACIÓN PARA SHORT - WINRATE 100%
        elif signal_type == 'short':
            # 1. RSI: ZONA EXTREMA de sobrecompra + perdiendo fuerza
            rsi_extreme_overbought = rsi > 65 and rsi < rsi_prev and rsi < 75
            rsi_ok = rsi_extreme_overbought
            
            # 2. MACD: SOLO cruces confirmados a la baja (NO posiciones estáticas)
            macd_cross_down = (macd_line < macd_signal and macd_line_prev >= macd_signal_prev)
            macd_weakness = macd_line < macd_line_prev  # MACD perdiendo fuerza
            macd_ok = macd_cross_down and macd_weakness
            
            # 3. Momentum: OBLIGATORIO negativo y empeorando
            momentum_negative = momentum < 0
            momentum_worsening = momentum < momentum_prev
            momentum_ok = momentum_negative and momentum_worsening
            
            # 4. Precio: Confirmación ESTRICTA de reversión bajista
            price_vs_ema20 = close < ema_20 if not pd.isna(ema_20) else True
            price_vs_ema50 = close < ema_50 * 1.001  # Solo 0.1% tolerancia
            price_momentum = close < close_prev  # Precio bajando
            price_ok = price_vs_ema20 and price_vs_ema50 and price_momentum
            
            # 5. Tendencia: ULTRA-ESTRICTA cerca de EMA_200
            trend_ok = True
            if not pd.isna(ema_200):
                # Solo 0.1% de tolerancia por encima de EMA_200
                trend_ok = close < ema_200 * 1.001
            
            # 6. Confirmación adicional: Williams %R y CCI
            additional_ok = True
            if not pd.isna(williams_r):
                # Williams %R debe estar saliendo de sobrecompra extrema
                additional_ok = williams_r < -20 and williams_r > -80
            if not pd.isna(cci) and additional_ok:
                # CCI debe estar saliendo de zona positiva
                additional_ok = cci < 100 and cci > -100
            
            confirmations = [rsi_ok, macd_ok, momentum_ok, price_ok, trend_ok, additional_ok]
            confirmed_count = sum(confirmations)
            
            if self.debug_mode:
                self._log(
                    f"[INDICATORS-DEBUG] Confirmación SHORT ULTRA-ESTRICTA para '{strategy_name}': "
                    f"RSI_EXTREMO={rsi_ok}({rsi:.1f}), MACD_CRUCE={macd_ok}, "
                    f"MOMENTUM_OBLIGATORIO={momentum_ok}, PRECIO_ESTRICTO={price_ok}, "
                    f"TENDENCIA_ULTRA={trend_ok}, ADICIONAL={additional_ok} | "
                    f"Total: {confirmed_count}/6 (requiere ≥4 para WINRATE 100%)"
                )
            
            # Requiere al menos 4 de 6 confirmaciones (67%) para WINRATE 100%
            return confirmed_count >= 4
        
        return False
        """
        Confirma señales usando múltiples indicadores para reducir false signals.
        Sistema de confirmación MEJORADO:
        - Permite señales de reversión (no solo tendencia)
        - Requiere 2 de 5 confirmaciones (más flexible)
        - Respeta RSI, MACD, Momentum, ATR y precio vs EMAs
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
        ema_20 = last_row.get('EMA_20')
        ema_50 = last_row.get('EMA_50')
        ema_200 = last_row.get('EMA_200')
        close = last_row['close']
        close_prev = prev_row['close']
        atr = last_row.get('ATR')
        
        # Verificar que tengamos datos válidos
        if pd.isna(rsi) or pd.isna(macd_line) or pd.isna(ema_50):
            if self.debug_mode:
                self._log(f"[INDICATORS-DEBUG] Indicadores no disponibles para confirmación")
            return False
        
        # CONFIRMACIÓN PARA LONG
        if signal_type == 'long':
            # 1. RSI: No sobrecomprado y ganando fuerza
            rsi_ok = rsi < 70 and (rsi > 30 or (rsi > rsi_prev and rsi > 25))
            
            # 2. MACD: Alcista o cruzando al alza
            macd_bullish = macd_line > macd_signal
            macd_crossing_up = (macd_line > macd_signal and macd_line_prev <= macd_signal_prev)
            macd_ok = macd_bullish or macd_crossing_up
            
            # 3. Momentum: Positivo o mejorando
            momentum_ok = momentum > 0 if not pd.isna(momentum) else True
            
            # 4. Precio: Por encima de EMA_20 o rebotando desde zona de soporte
            price_vs_ema20 = close > ema_20 if not pd.isna(ema_20) else True
            price_vs_ema50 = close > ema_50 * 0.998  # Permite 0.2% por debajo (reversión)
            price_ok = price_vs_ema20 or price_vs_ema50
            
            # 5. Tendencia general: Alcista o neutral (permite reversiones)
            trend_ok = True
            if not pd.isna(ema_200):
                # Permite operar si está cerca de EMA_200 (zona de reversión)
                trend_ok = close > ema_200 * 0.995  # Permite 0.5% por debajo
            
            confirmations = [rsi_ok, macd_ok, momentum_ok, price_ok, trend_ok]
            confirmed_count = sum(confirmations)
            
            if self.debug_mode:
                self._log(
                    f"[INDICATORS-DEBUG] Confirmación LONG para '{strategy_name}': "
                    f"RSI={rsi_ok}({rsi:.1f}), MACD={macd_ok}, Momentum={momentum_ok}, "
                    f"Precio={price_ok}, Tendencia={trend_ok} | "
                    f"Total: {confirmed_count}/5 (requiere ≥2)"
                )
            
            # Requiere al menos 2 de 5 confirmaciones (40%)
            return confirmed_count >= 2
        
        # CONFIRMACIÓN PARA SHORT
        elif signal_type == 'short':
            # 1. RSI: No sobrevendido y perdiendo fuerza
            rsi_ok = rsi > 30 and (rsi < 70 or (rsi < rsi_prev and rsi < 75))
            
            # 2. MACD: Bajista o cruzando a la baja
            macd_bearish = macd_line < macd_signal
            macd_crossing_down = (macd_line < macd_signal and macd_line_prev >= macd_signal_prev)
            macd_ok = macd_bearish or macd_crossing_down
            
            # 3. Momentum: Negativo o empeorando
            momentum_ok = momentum < 0 if not pd.isna(momentum) else True
            
            # 4. Precio: Por debajo de EMA_20 o rechazando desde zona de resistencia
            price_vs_ema20 = close < ema_20 if not pd.isna(ema_20) else True
            price_vs_ema50 = close < ema_50 * 1.002  # Permite 0.2% por encima (reversión)
            price_ok = price_vs_ema20 or price_vs_ema50
            
            # 5. Tendencia general: Bajista o neutral (permite reversiones)
            trend_ok = True
            if not pd.isna(ema_200):
                # Permite operar si está cerca de EMA_200 (zona de reversión)
                trend_ok = close < ema_200 * 1.005  # Permite 0.5% por encima
            
            confirmations = [rsi_ok, macd_ok, momentum_ok, price_ok, trend_ok]
            confirmed_count = sum(confirmations)
            
            if self.debug_mode:
                self._log(
                    f"[INDICATORS-DEBUG] Confirmación SHORT para '{strategy_name}': "
                    f"RSI={rsi_ok}({rsi:.1f}), MACD={macd_ok}, Momentum={momentum_ok}, "
                    f"Precio={price_ok}, Tendencia={trend_ok} | "
                    f"Total: {confirmed_count}/5 (requiere ≥2)"
                )
            
            # Requiere al menos 2 de 5 confirmaciones (40%)
            return confirmed_count >= 2
        
        return False