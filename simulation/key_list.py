"""
Mapeo de nombres de estrategias o patrones de velas a IDs numéricos únicos.
"""

import os

# Lista de patrones de velas extraídos de candles/candle_list.py
CANDLE_PATTERNS = [
    "hammer", "shooting_star", "marubozu", "dragonfly_doji", 
    "gravestone_doji", "hanging_man", "inverted_hammer", "morning_star",
    "doji", "long_legged_doji", "doji_reversal", "engulfing", "harami",
    "piercing_line", "dark_cloud_cover", "evening_star", "three_white_soldiers",
    "three_black_crows", "three_inside_up_down", "three_outside_up_down",
    "rising_three_methods", "falling_three_methods"
]


STRATEGY_NAMES = [
    "forex_strategy_price_action_sr",
    "forex_strategy_ma_crossover",
    "forex_strategy_momentum_rsi_macd",
    "forex_strategy_bollinger_bands_breakout",
    "forex_strategy_ichimoku_kinko_hyo",
    "forex_strategy_swing_trading_multi_indicator",
    "forex_strategy_candle_pattern_reversal",
    "forex_strategy_scalping_stochrsi_ema",
    "forex_strategy_fibonacci_reversal",
    "forex_strategy_chart_pattern_breakout",
    "forex_strategy_hybrid_optimizer"
]

def get_id_for_name(name: str) -> int:
    """
    Devuelve un ID numérico único para un nombre de estrategia o patrón de vela dado.

    Args:
        name (str): El nombre de la estrategia o patrón.

    Returns:
        int: El ID numérico único, o -1 si el nombre no se encuentra.
    """
    selected = STRATEGY_NAMES.index(name)
    if selected == -1:
        return -1
    return selected


def get_name_for_id(id: int) -> str:
    """
    Devuelve el nombre de la estrategia o patrón de vela correspondiente a un ID numérico dado.

    Args:
        id (int): El ID numérico único.

    Returns:
        str: El nombre de la estrategia o patrón, o "" si el ID no se encuentra.
    """
    if id < 0 or id >= len(STRATEGY_NAMES):
        return ""
    return STRATEGY_NAMES[id]