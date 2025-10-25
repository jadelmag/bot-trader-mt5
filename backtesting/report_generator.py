import os
import json
from datetime import datetime

class ReportGenerator:
    """Genera informes detallados de las sesiones de backtesting."""

    def __init__(self, profitable_trades, summary_lines, total_profit, symbol, timeframe, strategies_config=None):
        """
        Inicializa el generador de informes.

        Args:
            profitable_trades (list): Lista de diccionarios, cada uno representando una operación rentable.
            summary_lines (list): Líneas de texto del resumen general.
            total_profit (float): Beneficio total del backtest.
            symbol (str): Símbolo del activo (ej. 'EURUSD').
            timeframe (str): Timeframe del gráfico (ej. 'M1').
            strategies_config (dict): Configuración de estrategias y patrones.
        """
        self.profitable_trades = profitable_trades
        self.summary_lines = summary_lines
        self.total_profit = total_profit
        self.symbol = symbol
        self.timeframe = timeframe
        self.strategies_config = strategies_config or self._load_strategies_config()
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
                
                # Escribir configuración de estrategias y patrones
                self._write_strategies_configuration(f)
                
                # Escribir configuración específica de patrones que generaron operaciones
                self._write_pattern_configurations_used(f)
            
            return filepath
        except Exception as e:
            print(f"Error al generar el informe: {e}")
            return None
    
    def _load_strategies_config(self):
        """Carga la configuración de estrategias desde el archivo JSON."""
        try:
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'strategies', 'strategies.json')
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error al cargar configuración de estrategias: {e}")
            return {}
    
    def _write_strategies_configuration(self, f):
        """Escribe la configuración de estrategias y patrones en el informe."""
        if not self.strategies_config:
            return
        
        f.write("\n\n")
        f.write("--- CONFIGURACIÓN DE ESTRATEGIAS ACTIVAS ---\n")
        
        # Estrategias Forex
        forex_strategies = self.strategies_config.get('forex_strategies', {})
        active_forex = {k: v for k, v in forex_strategies.items() if v.get('selected', False)}
        
        if active_forex:
            f.write("\n** ESTRATEGIAS FOREX **\n")
            f.write("-" * 50 + "\n")
            for strategy_name, config in active_forex.items():
                clean_name = strategy_name.replace('strategy_', '').replace('_', ' ').title()
                f.write(f"• {clean_name}:\n")
                f.write(f"  - Ratio de Porcentaje: {config.get('percent_ratio', 'N/A')}\n")
                f.write(f"  - Ratio R/R: {config.get('rr_ratio', 'N/A')}\n")
                f.write(f"  - Stop Loss (pips): {config.get('stop_loss_pips', 'N/A')}\n")
                f.write("\n")
        
        # Patrones de Velas
        candle_strategies = self.strategies_config.get('candle_strategies', {})
        active_candles = {k: v for k, v in candle_strategies.items() if v.get('selected', False)}
        
        if active_candles:
            f.write("** PATRONES DE VELAS **\n")
            f.write("-" * 50 + "\n")
            for pattern_name, config in active_candles.items():
                clean_name = pattern_name.replace('is_', '').replace('_', ' ').title()
                f.write(f"• {clean_name}:\n")
                f.write(f"  - Modo de Estrategia: {config.get('strategy_mode', 'N/A')}\n")
                
                # Cargar configuración detallada del patrón
                pattern_config = self._load_pattern_config(pattern_name)
                if pattern_config:
                    f.write(f"  - Use Signal Change: {pattern_config.get('use_signal_change', 'N/A')}\n")
                    f.write(f"  - Use Stop Loss: {pattern_config.get('use_stop_loss', 'N/A')}\n")
                    f.write(f"  - Use Take Profit: {pattern_config.get('use_take_profit', 'N/A')}\n")
                    f.write(f"  - Use Trailing Stop: {pattern_config.get('use_trailing_stop', 'N/A')}\n")
                    f.write(f"  - Use Pattern Reversal: {pattern_config.get('use_pattern_reversal', 'N/A')}\n")
                    f.write(f"  - Percent Ratio: {pattern_config.get('percent_ratio', 'N/A')}\n")
                    f.write(f"  - ATR SL Multiplier: {pattern_config.get('atr_sl_multiplier', 'N/A')}\n")
                    f.write(f"  - ATR TP Multiplier: {pattern_config.get('atr_tp_multiplier', 'N/A')}\n")
                    f.write(f"  - ATR Trailing Multiplier: {pattern_config.get('atr_trailing_multiplier', 'N/A')}\n")
                f.write("\n")
        
        # Estrategias Personalizadas
        custom_strategies = self.strategies_config.get('custom_strategies', {})
        active_custom = {k: v for k, v in custom_strategies.items() if v.get('selected', False)}
        
        if active_custom:
            f.write("** ESTRATEGIAS PERSONALIZADAS **\n")
            f.write("-" * 50 + "\n")
            for strategy_name, config in active_custom.items():
                clean_name = strategy_name.replace('run_', '').replace('_', ' ').title()
                f.write(f"• {clean_name}: Activa\n")
                f.write("\n")
        
        # Configuración de slots
        slots = self.strategies_config.get('slots', {})
        if slots:
            f.write("** CONFIGURACIÓN DE SLOTS **\n")
            f.write("-" * 50 + "\n")
            f.write(f"• Forex: {slots.get('forex', 0)} slots\n")
            f.write(f"• Velas: {slots.get('candle', 0)} slots\n")
            f.write(f"• Personalizadas: {slots.get('custom', 0)} slots\n")
    
    def _load_pattern_config(self, pattern_name):
        """Carga la configuración detallada de un patrón de vela desde su archivo JSON."""
        try:
            # Mapear nombres de señales a nombres de archivos
            # Los nombres en el informe vienen como "Dark Cloud Cover", "Doji Reversal", etc.
            name_mapping = {
                'Dark Cloud Cover': 'dark_cloud_cover',
                'Doji': 'doji',
                'Doji Reversal': 'doji_reversal',
                'Dragonfly Doji': 'dragonfly_doji',
                'Engulfing': 'engulfing',
                'Evening Star': 'evening_star',
                'Falling Three Methods': 'falling_three_methods',
                'Gravestone Doji': 'gravestone_doji',
                'Hammer': 'hammer',
                'Hanging Man': 'hanging_man',
                'Harami': 'harami',
                'Inverted Hammer': 'inverted_hammer',
                'Long Legged Doji': 'long_legged_doji',
                'Marubozu': 'marubozu',
                'Morning Star': 'morning_star',
                'Piercing Line': 'piercing_line',
                'Rising Three Methods': 'rising_three_methods',
                'Shooting Star': 'shooting_star',
                'Three Black Crows': 'three_black_crows',
                'Three Inside Up Down': 'three_inside_up_down',
                'Three Outside Up Down': 'three_outside_up_down',
                'Three White Soldiers': 'three_white_soldiers'
            }
            
            # Convertir el nombre de la señal al nombre del archivo
            clean_pattern_name = pattern_name.replace('pattern_', '').replace('is_', '').replace('_', ' ').title()
            file_base_name = name_mapping.get(clean_pattern_name)
            
            if not file_base_name:
                # Fallback: intentar convertir directamente
                file_base_name = pattern_name.replace('pattern_', '').replace('is_', '').lower()
            
            file_name = file_base_name + '.json'
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'strategies', file_name)
            
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return None
        except Exception as e:
            print(f"Error al cargar configuración del patrón {pattern_name}: {e}")
            return None
    
    def _calculate_optimal_config(self, pattern_trades, current_config):
        """Calcula la configuración óptima para maximizar beneficios de un patrón."""
        if not pattern_trades or not current_config:
            return None
        
        try:
            # Rangos de optimización para ATR multipliers
            sl_multipliers = [0.5, 0.8, 1.0, 1.2, 1.5, 1.8, 2.0, 2.5, 3.0]
            tp_multipliers = [1.0, 1.2, 1.5, 1.8, 2.0, 2.5, 3.0, 3.5, 4.0]
            
            best_profit = 0
            best_sl_mult = current_config.get('atr_sl_multiplier', 1.5)
            best_tp_mult = current_config.get('atr_tp_multiplier', 2.0)
            best_profitable_ops = 0
            best_winrate = 0
            
            # Probar todas las combinaciones
            for sl_mult in sl_multipliers:
                for tp_mult in tp_multipliers:
                    # Calcular beneficio potencial con esta configuración
                    total_profit, profitable_ops, winrate = self._simulate_config(
                        pattern_trades, sl_mult, tp_mult
                    )
                    
                    # Si esta configuración es mejor, guardarla
                    if total_profit > best_profit:
                        best_profit = total_profit
                        best_sl_mult = sl_mult
                        best_tp_mult = tp_mult
                        best_profitable_ops = profitable_ops
                        best_winrate = winrate
            
            return {
                'optimal_sl_multiplier': best_sl_mult,
                'optimal_tp_multiplier': best_tp_mult,
                'max_potential_profit': best_profit,
                'profitable_operations': best_profitable_ops,
                'optimal_winrate': best_winrate
            }
            
        except Exception as e:
            print(f"Error al calcular configuración óptima: {e}")
            return None
    
    def _simulate_config(self, trades, sl_multiplier, tp_multiplier):
        """Simula el resultado de las operaciones con una configuración específica."""
        total_profit = 0
        profitable_operations = 0
        total_operations = len(trades)
        
        for trade in trades:
            entry_price = trade.get('entry_price', 0)
            exit_price = trade.get('exit_price', 0)
            trade_type = trade.get('type', 'long')
            
            # Simular ATR (aproximación basada en el movimiento real)
            price_movement = abs(exit_price - entry_price)
            estimated_atr = price_movement * 2  # Estimación conservadora
            
            # Calcular SL y TP con los nuevos multipliers
            if trade_type == 'long':
                sl_price = entry_price - (estimated_atr * sl_multiplier)
                tp_price = entry_price + (estimated_atr * tp_multiplier)
                
                # Determinar si habría sido rentable
                if exit_price >= tp_price:
                    # TP alcanzado
                    profit = (tp_price - entry_price) * 100000  # Convertir a pips aprox
                    total_profit += profit
                    profitable_operations += 1
                elif exit_price <= sl_price:
                    # SL alcanzado
                    loss = (sl_price - entry_price) * 100000
                    total_profit += loss  # loss será negativo
                else:
                    # Salida manual en el precio real
                    profit = (exit_price - entry_price) * 100000
                    total_profit += profit
                    if profit > 0:
                        profitable_operations += 1
            
            else:  # short
                sl_price = entry_price + (estimated_atr * sl_multiplier)
                tp_price = entry_price - (estimated_atr * tp_multiplier)
                
                if exit_price <= tp_price:
                    # TP alcanzado
                    profit = (entry_price - tp_price) * 100000
                    total_profit += profit
                    profitable_operations += 1
                elif exit_price >= sl_price:
                    # SL alcanzado
                    loss = (entry_price - sl_price) * 100000
                    total_profit += loss  # loss será negativo
                else:
                    # Salida manual en el precio real
                    profit = (entry_price - exit_price) * 100000
                    total_profit += profit
                    if profit > 0:
                        profitable_operations += 1
        
        winrate = (profitable_operations / total_operations * 100) if total_operations > 0 else 0
        return total_profit, profitable_operations, winrate
    
    def _write_pattern_configurations_used(self, f):
        """Escribe la configuración específica y optimizada de cada patrón que generó operaciones rentables."""
        if not self.profitable_trades:
            return
        
        # Obtener patrones únicos que generaron operaciones
        patterns_used = set()
        for trade in self.profitable_trades:
            signal_name = trade.get('signal_name', '')
            if not signal_name.startswith('strategy_'):  # Solo patrones de velas
                patterns_used.add(signal_name)
        
        if not patterns_used:
            return
        
        f.write("\n\n")
        f.write("--- ANÁLISIS DE OPTIMIZACIÓN DE PATRONES DE VELAS ---\n")
        f.write("\n")
        
        for pattern_name in sorted(patterns_used):
            # Convertir nombre para mostrar
            clean_name = pattern_name.replace('pattern_', '').replace('is_', '').replace('_', ' ').title()
            
            # Obtener operaciones de este patrón
            pattern_trades = [t for t in self.profitable_trades if t.get('signal_name') == pattern_name]
            
            # Cargar configuración actual del patrón
            pattern_config = self._load_pattern_config(pattern_name)
            
            # Calcular configuración óptima
            optimal_config = self._calculate_optimal_config(pattern_trades, pattern_config)
            
            f.write(f"** {clean_name.upper()} **\n")
            f.write("=" * 60 + "\n")
            
            # Configuración actual
            f.write("CONFIGURACIÓN ACTUAL:\n")
            f.write("-" * 30 + "\n")
            if pattern_config:
                f.write(f"  • Use Signal Change: {pattern_config.get('use_signal_change', 'N/A')}\n")
                f.write(f"  • Use Stop Loss: {pattern_config.get('use_stop_loss', 'N/A')}\n")
                f.write(f"  • Use Take Profit: {pattern_config.get('use_take_profit', 'N/A')}\n")
                f.write(f"  • Use Trailing Stop: {pattern_config.get('use_trailing_stop', 'N/A')}\n")
                f.write(f"  • Use Pattern Reversal: {pattern_config.get('use_pattern_reversal', 'N/A')}\n")
                f.write(f"  • Percent Ratio: {pattern_config.get('percent_ratio', 'N/A')}\n")
                f.write(f"  • ATR SL Multiplier: {pattern_config.get('atr_sl_multiplier', 'N/A')}\n")
                f.write(f"  • ATR TP Multiplier: {pattern_config.get('atr_tp_multiplier', 'N/A')}\n")
                f.write(f"  • ATR Trailing Multiplier: {pattern_config.get('atr_trailing_multiplier', 'N/A')}\n")
            
            # Resultados actuales
            total_profit_actual = sum(t.get('profit', 0) for t in pattern_trades)
            f.write(f"\n  • Operaciones Rentables: {len(pattern_trades)}\n")
            f.write(f"  • Beneficio Total Actual: {total_profit_actual:.2f} $\n")
            
            # Configuración óptima
            f.write("\nCONFIGURACIÓN ÓPTIMA CALCULADA:\n")
            f.write("-" * 30 + "\n")
            if optimal_config:
                f.write(f"  • ATR SL Multiplier Óptimo: {optimal_config['optimal_sl_multiplier']:.2f}\n")
                f.write(f"  • ATR TP Multiplier Óptimo: {optimal_config['optimal_tp_multiplier']:.2f}\n")
                f.write(f"  • Beneficio Potencial Máximo: {optimal_config['max_potential_profit']:.2f} $\n")
                
                improvement = ((optimal_config['max_potential_profit'] - total_profit_actual) / total_profit_actual * 100) if total_profit_actual > 0 else 0
                f.write(f"  • Mejora Potencial: {improvement:+.1f}%\n")
                
                f.write(f"\n  • Operaciones que habrían sido rentables: {optimal_config['profitable_operations']}\n")
                f.write(f"  • Winrate Óptimo: {optimal_config['optimal_winrate']:.1f}%\n")
            else:
                f.write("  • No se pudo calcular configuración óptima\n")
            
            f.write("\n")
