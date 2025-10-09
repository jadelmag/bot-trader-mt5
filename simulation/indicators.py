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
        Añade columnas al DataFrame: RSI, ATR, MACD, Momentum, EMAs, Bollinger Bands.
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
            
            # --- EMAs para tendencia ---
            candles_df['EMA_50'] = ta.ema(df['Close'], length=50)
            candles_df['EMA_200'] = ta.ema(df['Close'], length=200)
            
            # --- Bollinger Bands (20, 2) ---
            candles_df = self._calculate_bollinger_bands(df, candles_df)
            
            # --- Crear aliases para compatibilidad ---
            candles_df = self._create_aliases(candles_df)
            
            # --- EMAs adicionales para strategy_ma_crossover ---
            candles_df['ema_fast'] = ta.ema(df['Close'], length=10)
            candles_df['ema_slow'] = ta.ema(df['Close'], length=50)
            
            if self.debug_mode:
                last_row = candles_df.iloc[-1]
                self._log(
                    f"[INDICATORS-DEBUG] Indicadores calculados - "
                    f"RSI: {last_row.get('RSI', 'N/A'):.2f if not pd.isna(last_row.get('RSI')) else 'N/A'}, "
                    f"ATR: {last_row.get('ATR', 'N/A'):.5f if not pd.isna(last_row.get('ATR')) else 'N/A'}, "
                    f"MACD: {last_row.get('MACD_line', 'N/A'):.5f if not pd.isna(last_row.get('MACD_line')) else 'N/A'}"
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
            # Verificar que las columnas existan antes de acceder
            if 'BBU_20_2.0' in bb.columns:
                candles_df['BB_upper'] = bb['BBU_20_2.0']
                candles_df['BB_middle'] = bb['BBM_20_2.0']
                candles_df['BB_lower'] = bb['BBL_20_2.0']
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
        
        return candles_df
    
    def confirm_signal_with_indicators(self, candles_df, signal_type, strategy_name=None):
        """
        Confirma señales usando múltiples indicadores para reducir false signals.
        Requiere al menos 3 de 4 confirmaciones para aprobar una señal.
        """
        if candles_df.empty or len(candles_df) < 50:
            return False
        
        last_row = candles_df.iloc[-1]
        
        # Obtener indicadores
        rsi = last_row.get('RSI')
        macd_line = last_row.get('MACD_line')
        macd_signal = last_row.get('MACD_signal')
        momentum = last_row.get('Momentum')
        ema_50 = last_row.get('EMA_50')
        close = last_row['close']
        
        # Verificar que tengamos datos válidos
        if pd.isna(rsi) or pd.isna(macd_line) or pd.isna(ema_50):
            if self.debug_mode:
                self._log(f"[INDICATORS-DEBUG] Indicadores no disponibles para confirmación")
            return False
        
        # CONFIRMACIÓN PARA LONG
        if signal_type == 'long':
            trend_ok = close > ema_50
            rsi_ok = 30 < rsi < 70
            macd_ok = macd_line > macd_signal
            momentum_ok = momentum > 0 if not pd.isna(momentum) else True
            
            confirmations = [trend_ok, rsi_ok, macd_ok, momentum_ok]
            confirmed_count = sum(confirmations)
            
            if self.debug_mode:
                self._log(
                    f"[INDICATORS-DEBUG] Confirmación LONG para '{strategy_name}': "
                    f"Tendencia={trend_ok}, RSI={rsi_ok}({rsi:.1f}), "
                    f"MACD={macd_ok}, Momentum={momentum_ok} | "
                    f"Total: {confirmed_count}/4"
                )
            
            return confirmed_count >= 3
        
        # CONFIRMACIÓN PARA SHORT
        elif signal_type == 'short':
            trend_ok = close < ema_50
            rsi_ok = 30 < rsi < 70
            macd_ok = macd_line < macd_signal
            momentum_ok = momentum < 0 if not pd.isna(momentum) else True
            
            confirmations = [trend_ok, rsi_ok, macd_ok, momentum_ok]
            confirmed_count = sum(confirmations)
            
            if self.debug_mode:
                self._log(
                    f"[INDICATORS-DEBUG] Confirmación SHORT para '{strategy_name}': "
                    f"Tendencia={trend_ok}, RSI={rsi_ok}({rsi:.1f}), "
                    f"MACD={macd_ok}, Momentum={momentum_ok} | "
                    f"Total: {confirmed_count}/4"
                )
            
            return confirmed_count >= 3
        
        return False