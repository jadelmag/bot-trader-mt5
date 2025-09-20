import pandas as pd
import pandas_ta as ta


def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Añade un conjunto completo de indicadores técnicos a un DataFrame de velas.

    Args:
        df (pd.DataFrame): DataFrame con columnas 'open', 'high', 'low', 'close'.

    Returns:
        pd.DataFrame: El DataFrame original con los indicadores añadidos como nuevas columnas.
    """
    if df.empty:
        return df

    # --- Medias Móviles Exponenciales (EMAs) ---
    df.ta.ema(length=12, append=True, col_names=('ema_fast',))
    df.ta.ema(length=26, append=True, col_names=('ema_slow',))
    df.ta.ema(length=50, append=True, col_names=('ema_50',))
    df.ta.ema(length=200, append=True, col_names=('ema_200',))

    # --- Índice de Fuerza Relativa (RSI) ---
    df.ta.rsi(length=14, append=True, col_names=('rsi',))

    # --- MACD ---
    # Los nombres de columna por defecto son 'MACD_12_26_9', 'MACDh_12_26_9', 'MACDs_12_26_9'
    macd = df.ta.macd(fast=12, slow=26, signal=9, append=True)
    if macd is not None and not macd.empty:
        df.rename(columns={
            'MACD_12_26_9': 'macd_line',
            'MACDh_12_26_9': 'macd_hist',
            'MACDs_12_26_9': 'macd_signal'
        }, inplace=True)

    # --- Bandas de Bollinger (BBands) ---
    # Nombres por defecto: 'BBL_20_2.0', 'BBM_20_2.0', 'BBU_20_2.0', 'BBB_20_2.0', 'BBP_20_2.0'
    bbands = df.ta.bbands(length=20, std=2, append=True)
    if bbands is not None and not bbands.empty:
        df.rename(columns={
            'BBL_20_2.0': 'bb_lower',
            'BBM_20_2.0': 'bb_middle',
            'BBU_20_2.0': 'bb_upper'
        }, inplace=True)

    # --- Ichimoku Kinko Hyo ---
    # Nombres por defecto: 'ITS_9', 'IKS_26', 'ISA_9_26_52', 'ISB_26_52', 'ICS_26'
    ichimoku = df.ta.ichimoku(append=True)
    if ichimoku is not None and not ichimoku.empty:
        df.rename(columns={
            'ITS_9': 'tenkan_sen',
            'IKS_26': 'kijun_sen',
            'ISA_9_26_52': 'senkou_span_a',
            'ISB_26_52': 'senkou_span_b',
            'ICS_26': 'chikou_span'
        }, inplace=True)

    # --- Stochastic RSI (StochRSI) ---
    # Nombres por defecto: 'STOCHRSIk_14_14_3_3', 'STOCHRSId_14_14_3_3'
    stoch_rsi = df.ta.stochrsi(append=True)
    if stoch_rsi is not None and not stoch_rsi.empty:
        df.rename(columns={
            'STOCHRSIk_14_14_3_3': 'stochrsi_k',
            'STOCHRSId_14_14_3_3': 'stochrsi_d'
        }, inplace=True)

    # --- Average True Range (ATR) ---
    df.ta.atr(length=14, append=True, col_names=('atr',))

    # Eliminar filas con NaN generadas por los cálculos de los indicadores
    df.dropna(inplace=True)
    df.reset_index(drop=True, inplace=True)

    return df
