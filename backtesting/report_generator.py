import os
from datetime import datetime

class ReportGenerator:
    """Genera informes detallados de las sesiones de backtesting."""

    def __init__(self, profitable_trades, summary_lines, total_profit, symbol, timeframe):
        """
        Inicializa el generador de informes.

        Args:
            profitable_trades (list): Lista de diccionarios, cada uno representando una operación rentable.
            summary_lines (list): Líneas de texto del resumen general.
            total_profit (float): Beneficio total del backtest.
            symbol (str): Símbolo del activo (ej. 'EURUSD').
            timeframe (str): Timeframe del gráfico (ej. 'M1').
        """
        self.profitable_trades = profitable_trades
        self.summary_lines = summary_lines
        self.total_profit = total_profit
        self.symbol = symbol
        self.timeframe = timeframe
        self.report_dir = "resumes"

    def generate_report(self):
        """Crea y guarda el informe detallado en un archivo de texto."""
        try:
            # Asegurarse de que el directorio de informes existe
            os.makedirs(self.report_dir, exist_ok=True)

            # Generar nombre de archivo con fecha y hora
            now = datetime.now()
            filename = f"backtesting_{now.strftime('%d-%m-%Y_%H-%M-%S')}.txt"
            filepath = os.path.join(self.report_dir, filename)

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("="*80 + "\n")
                f.write(f"INFORME DETALLADO DE BACKTESTING\n")
                f.write("="*80 + "\n")
                f.write(f"Fecha y Hora: {now.strftime('%d/%m/%Y %H:%M:%S')}\n")
                f.write(f"Activo: {self.symbol}\n")
                f.write(f"Timeframe: {self.timeframe}\n")
                f.write("\n\n")

                # Escribir el resumen general
                f.write("--- RESUMEN GENERAL ---\n")
                for line in self.summary_lines:
                    f.write(line + "\n")
                f.write(f"\nBENEFICIO TOTAL PERFECTO: {self.total_profit:.2f} $\n")
                f.write("\n\n")

                # Escribir el detalle de operaciones rentables
                f.write("--- DETALLE DE OPERACIONES RENTABLES ---\n")
                header = f"{'FECHA ENTRADA':<22} | {'SEÑAL':<35} | {'TIPO':<7} | {'ENTRADA':>10} | {'SALIDA':>10} | {'BENEFICIO':>12}\n"
                f.write(header)
                f.write("-"*len(header) + "\n")

                # Ordenar trades por fecha
                sorted_trades = sorted(self.profitable_trades, key=lambda x: x['entry_time'])

                for trade in sorted_trades:
                    clean_name = trade['signal_name'].replace('strategy_', '').replace('pattern_', '').replace('_', ' ').title()
                    entry_time_str = trade['entry_time'].strftime('%d/%m/%Y %H:%M')
                    line = f"{entry_time_str:<22} | {clean_name:<35} | {trade['type']:<7} | {trade['entry_price']:>10.5f} | {trade['exit_price']:>10.5f} | {f'{trade['profit']:.2f} $':>12}\n"
                    f.write(line)
            
            return filepath
        except Exception as e:
            print(f"Error al generar el informe: {e}")
            return None
