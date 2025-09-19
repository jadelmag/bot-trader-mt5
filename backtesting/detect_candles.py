import pandas as pd
import os
import sys

# Añadir el directorio raíz del proyecto a sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from candles.candle_list import CandlePatterns

class CandleDetector:
    def __init__(self, candles_df):
        """
        Inicializa el detector con un DataFrame de velas de pandas.
        El DataFrame debe tener columnas: 'open', 'high', 'low', 'close'.
        """
        if not isinstance(candles_df, pd.DataFrame) or not all(c in candles_df for c in ['open', 'high', 'low', 'close']):
            raise ValueError("Se requiere un DataFrame de pandas con columnas 'open', 'high', 'low', 'close'.")
        # Convertir el DataFrame a una lista de diccionarios para compatibilidad con CandlePatterns
        self.candles = candles_df.to_dict('records')
        self.pattern_methods = self._get_pattern_methods()

    def _get_pattern_methods(self):
        """Obtiene un diccionario de nombres de patrones y sus funciones de detección."""
        methods = {}
        for func_name in dir(CandlePatterns):
            if func_name.startswith('is_'):
                pattern_name = func_name.replace('is_', '')
                methods[pattern_name] = getattr(CandlePatterns, func_name)
        return methods

    def analyze_patterns(self, selected_patterns, trade_duration=5, lot_size=0.01):
        """
        Analiza los patrones de velas seleccionados en todo el historial de datos.

        :param selected_patterns: Lista de nombres de patrones a detectar (ej: ['hammer', 'engulfing']).
        :param trade_duration: Número de velas que dura una operación simulada.
        :param lot_size: Tamaño del lote para el cálculo de ganancias/pérdidas.
        :return: Un diccionario con las estadísticas del análisis.
        """
        stats = {p: self._get_default_stats() for p in selected_patterns}

        for i in range(len(self.candles) - trade_duration):
            for pattern_name in selected_patterns:
                if pattern_name not in self.pattern_methods:
                    continue

                detection_func = self.pattern_methods[pattern_name]
                signal = detection_func(self.candles, i)

                if signal and signal != 'neutral':
                    open_price = self.candles[i]['close']
                    close_price = self.candles[i + trade_duration]['close']
                    
                    # Simulación de la operación
                    profit = 0
                    if signal == 'long':
                        profit = (close_price - open_price) * (100000 * lot_size) # Cálculo para un par estándar
                        stats[pattern_name]['money_generated_long'] += profit
                    elif signal == 'short':
                        profit = (open_price - close_price) * (100000 * lot_size)
                        stats[pattern_name]['money_generated_short'] += profit

                    # Actualizar estadísticas
                    stats[pattern_name]['appearances'] += 1
                    stats[pattern_name]['direction'] = signal
                    if profit > 0:
                        stats[pattern_name]['total_profit'] += profit
                    else:
                        stats[pattern_name]['total_loss'] += abs(profit)
        return stats

    @staticmethod
    def format_analysis_summary(stats):
        """
        Formatea las estadísticas de análisis de patrones en una tabla de texto.

        :param stats: El diccionario de estadísticas generado por analyze_patterns.
        :return: Una tupla con (lista_de_lineas_formateadas, total_profit, total_loss).
        """
        lines = []
        header = f"{'PATRÓN':<25} | {'DIRECCIÓN':<12} | {'APARICIONES':>12} | {'GANANCIA LONG':>15} | {'GANANCIA SHORT':>15} | {'GANANCIA TOTAL':>16} | {'PÉRDIDA TOTAL':>15}"
        lines.append("\n" + "="*15 + " RESUMEN DE ANÁLISIS DE PATRONES " + "="*15)
        lines.append(header)
        lines.append("-"*len(header))

        total_profit_all = 0
        total_loss_all = 0

        for pattern, data in stats.items():
            pattern_name = pattern.replace('_', ' ').title()
            direction = data['direction'].upper() if data['direction'] != 'N/A' else 'N/A'
            appearances = data['appearances']
            money_long = f"{data['money_generated_long']:.2f} $"
            money_short = f"{data['money_generated_short']:.2f} $"
            total_profit = f"{data['total_profit']:.2f} $"
            total_loss = f"{data['total_loss']:.2f} $"

            total_profit_all += data['total_profit']
            total_loss_all += data['total_loss']

            line = f"{pattern_name:<25} | {direction:<12} | {appearances:>12} | {money_long:>15} | {money_short:>15} | {total_profit:>16} | {total_loss:>15}"
            lines.append(line)

        lines.append("-"*len(header))
        return lines, total_profit_all, total_loss_all

    @staticmethod
    def _get_default_stats():
        """Devuelve la estructura de estadísticas por defecto para un patrón."""
        return {
            'appearances': 0,
            'direction': 'N/A',
            'money_generated_long': 0,
            'money_generated_short': 0,
            'total_profit': 0,
            'total_loss': 0
        }