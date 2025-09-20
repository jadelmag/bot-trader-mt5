import pandas as pd
import inspect
import os
import sys

# --- Configuración de sys.path ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from candles.candle_list import CandlePatterns
from forex.forex_list import ForexStrategies

class PerfectBacktester:
    """Realiza un backtesting 'perfecto' sabiendo el resultado futuro de las operaciones."""

    def __init__(self, df: pd.DataFrame, pip_value=10, hold_period=10):
        if not isinstance(df, pd.DataFrame) or df.empty:
            raise ValueError("Se requiere un DataFrame de pandas no vacío.")
        required_cols = ['open', 'high', 'low', 'close']
        if not all(col in df.columns for col in required_cols):
            raise ValueError(f"El DataFrame debe contener las columnas: {', '.join(required_cols)}")
        
        self.df = df
        self.candles_dict = df.to_dict('records')
        self.pip_value = pip_value
        self.hold_period = hold_period

    def _get_all_signals(self):
        """Obtiene todas las funciones de señales de patrones y estrategias."""
        signals = {}
        # Patrones de velas
        for name, func in inspect.getmembers(CandlePatterns, predicate=inspect.isfunction):
            if name.startswith('is_'):
                signals[name.replace('is_', 'pattern_')] = ('pattern', func)
        
        # Estrategias Forex
        for name, func in inspect.getmembers(ForexStrategies, predicate=inspect.isfunction):
            if name.startswith('strategy_'):
                signals[name] = ('strategy', func)
        return signals

    def run(self):
        """Ejecuta el backtesting perfecto sobre todo el DataFrame."""
        all_signals = self._get_all_signals()
        stats = {name: {'money_generated': 0, 'trades': 0} for name in all_signals.keys()}
        profitable_trades = []

        for i in range(len(self.df) - self.hold_period):
            for name, (signal_type, func) in all_signals.items():
                signal = None
                try:
                    if signal_type == 'pattern':
                        signal = func(self.candles_dict, i)
                    elif signal_type == 'strategy':
                        historical_df = self.df.iloc[:i+1]
                        signal = func(historical_df)
                except Exception:
                    continue # Ignorar si la señal falla por falta de datos

                if signal and signal != 'neutral':
                    entry_price = self.df['close'].iloc[i]
                    exit_price = self.df['close'].iloc[i + self.hold_period]
                    is_profitable = (signal == 'long' and exit_price > entry_price) or \
                                    (signal == 'short' and exit_price < entry_price)

                    if is_profitable:
                        pips_diff = abs(exit_price - entry_price) * 10000
                        profit = pips_diff * self.pip_value
                        stats[name]['money_generated'] += profit
                        stats[name]['trades'] += 1
                        profitable_trades.append({
                            'signal_name': name,
                            'type': signal, # 'long' o 'short'
                            'entry_index': i,
                            'exit_index': i + self.hold_period,
                            'entry_price': entry_price,
                            'exit_price': exit_price
                        })
        return stats, profitable_trades

    @staticmethod
    def format_summary(stats):
        """Formatea los resultados del backtesting perfecto en una tabla de texto."""
        lines = []
        header = f"{'SEÑAL (PATRÓN/ESTRATEGIA)':<50} | {'OPERACIONES RENTABLES':>25} | {'BENEFICIO TOTAL':>20}"
        lines.append("\n" + "="*25 + " RESUMEN DE BACKTESTING PERFECTO " + "="*25)
        lines.append(header)
        lines.append("-"*len(header))

        total_profit_all = 0
        # Filtrar y ordenar por beneficio
        sorted_stats = sorted(stats.items(), key=lambda item: item[1]['money_generated'], reverse=True)

        for name, data in sorted_stats:
            if data['trades'] > 0:
                clean_name = name.replace('strategy_', '').replace('pattern_', '').replace('_', ' ').title()
                
                signal_type = ""
                if name.startswith('pattern_'):
                    signal_type = "[candle]"
                elif name.startswith('strategy_'):
                    signal_type = "[forex]"

                display_name = f"{clean_name} {signal_type}"
                trades = data['trades']
                profit = f"{data['money_generated']:.2f} $"
                total_profit_all += data['money_generated']
                line = f"{display_name:<50} | {trades:>25} | {profit:>20}"
                lines.append(line)

        lines.append("-"*len(header))
        return lines, total_profit_all