import pandas as pd
import numpy as np
import os
import sys

# --- Configuración de sys.path ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from forex.forex_list import ForexStrategies

class StrategyAnalyzer:
    """Analiza un DataFrame de velas para encontrar señales de estrategias de Forex y calcula su rendimiento."""

    def __init__(self, df: pd.DataFrame, trade_amount=100000, pip_value=10, hold_period=10):
        if not isinstance(df, pd.DataFrame) or df.empty:
            raise ValueError("Se requiere un DataFrame de pandas no vacío.")
        required_cols = ['open', 'high', 'low', 'close']
        if not all(col in df.columns for col in required_cols):
            raise ValueError(f"El DataFrame debe contener las columnas: {', '.join(required_cols)}")
        
        self.df = df
        self.trade_amount = trade_amount  # Cantidad estándar por operación (ej. 1 lote)
        self.pip_value = pip_value        # Valor del pip para el par (ej. 10$ para EURUSD)
        self.hold_period = hold_period    # Número de velas que se mantiene la operación

    def analyze_strategies(self, selected_strategies: list):
        """
        Ejecuta el análisis para una lista de estrategias seleccionadas.

        Args:
            selected_strategies (list): Lista de nombres de métodos de estrategia a ejecutar.

        Returns:
            dict: Un diccionario con estadísticas para cada estrategia.
        """
        if not selected_strategies:
            return {}

        stats = {strategy: {
            'applications': 0,
            'money_generated': 0,
            'money_lost': 0
        } for strategy in selected_strategies}

        strategy_functions = {
            name: getattr(ForexStrategies, name) 
            for name in selected_strategies if hasattr(ForexStrategies, name)
        }

        # Iterar a través de cada vela en el DataFrame, dejando margen para el `hold_period`
        for i in range(len(self.df) - self.hold_period):
            # Crear un sub-dataframe con el historial hasta la vela actual
            historical_df = self.df.iloc[:i+1]

            for name, func in strategy_functions.items():
                try:
                    signal = func(historical_df)
                except Exception:
                    # Algunas estrategias pueden fallar si no tienen suficientes datos
                    continue

                if signal:
                    stats[name]['applications'] += 1
                    entry_price = self.df['close'].iloc[i]
                    exit_price = self.df['close'].iloc[i + self.hold_period]
                    
                    pips_diff = 0
                    if signal == 'long':
                        pips_diff = (exit_price - entry_price) * 10000 # Asumiendo 4 decimales
                    elif signal == 'short':
                        pips_diff = (entry_price - exit_price) * 10000

                    money_change = pips_diff * self.pip_value

                    if money_change > 0:
                        stats[name]['money_generated'] += money_change
                    else:
                        stats[name]['money_lost'] += abs(money_change)
        
        return stats

    @staticmethod
    def format_strategy_summary(stats):
        """
        Formatea las estadísticas de análisis de estrategias en una tabla de texto.

        :param stats: El diccionario de estadísticas generado por analyze_strategies.
        :return: Una tupla con (lista_de_lineas_formateadas, total_profit, total_loss).
        """
        lines = []
        header = f"{'ESTRATEGIA':<35} | {'APLICACIONES':>12} | {'BENEFICIOS':>15} | {'PÉRDIDAS':>15}"
        lines.append("\n" + "="*15 + " RESUMEN DE ANÁLISIS DE ESTRATEGIAS " + "="*15)
        lines.append(header)
        lines.append("-"*len(header))

        total_profit_all = 0
        total_loss_all = 0

        for strategy, data in stats.items():
            strategy_name = strategy.replace('strategy_', '').replace('_', ' ').title()
            applications = data['applications']
            benefits = f"{data['money_generated']:.2f} $"
            losses = f"{data['money_lost']:.2f} $"

            total_profit_all += data['money_generated']
            total_loss_all += data['money_lost']

            line = f"{strategy_name:<35} | {applications:>12} | {benefits:>15} | {losses:>15}"
            lines.append(line)

        lines.append("-"*len(header))
        return lines, total_profit_all, total_loss_all