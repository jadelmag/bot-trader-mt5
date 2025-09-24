try:
    from backtesting.detect_candles import CandleDetector
    from backtesting.apply_strategies import StrategyAnalyzer
    from backtesting.indicators import add_all_indicators
except ImportError as e:
    print(f"Error al importar módulos de análisis: {e}")
    CandleDetector = None
    StrategyAnalyzer = None
    add_all_indicators = None

class AnalysisHandler:
    def __init__(self, app):
        self.app = app

    def run_pattern_analysis(self, selected_patterns):
        """Ejecuta el análisis de patrones y muestra los resultados."""
        if not self.app.chart_started or not hasattr(self.app.graphic, 'candles_df') or self.app.graphic.candles_df is None:
            self.app._log_error("El gráfico no está iniciado o no hay datos de velas disponibles.")
            return
        
        if CandleDetector is None:
            self.app._log_error("El detector de velas no está disponible.")
            return

        try:
            candles_df_copy = self.app.graphic.candles_df.copy()
            candles_df_copy.columns = [col.lower() for col in candles_df_copy.columns]
            detector = CandleDetector(candles_df_copy)
            stats = detector.analyze_patterns(selected_patterns)

            summary_lines, total_profit, total_loss = CandleDetector.format_analysis_summary(stats)
            self.display_analysis_summary(summary_lines, total_profit, total_loss)

        except Exception as e:
            self.app._log_error(f"Ocurrió un error durante el análisis de patrones: {e}")

    def run_strategy_analysis(self, selected_strategies):
        """Ejecuta el análisis de estrategias y muestra los resultados."""
        if not self.app.chart_started or not hasattr(self.app.graphic, 'candles_df') or self.app.graphic.candles_df is None:
            self.app._log_error("El gráfico no está iniciado o no hay datos de velas disponibles.")
            return
        
        if StrategyAnalyzer is None or add_all_indicators is None:
            self.app._log_error("El analizador de estrategias o sus dependencias no están disponibles.")
            return

        try:
            candles_df_copy = self.app.graphic.candles_df.copy()
            candles_df_copy.columns = [col.lower() for col in candles_df_copy.columns]
            
            candles_df_copy = add_all_indicators(candles_df_copy)

            analyzer = StrategyAnalyzer(candles_df_copy)
            stats = analyzer.analyze_strategies(selected_strategies)

            self.display_strategy_summary(stats)

        except Exception as e:
            self.app._log_error(f"Ocurrió un error durante el análisis de estrategias: {e}")

    def display_analysis_summary(self, lines, total_profit, total_loss):
        """Muestra el resumen del análisis de patrones en el logger."""
        for line in lines:
            if "RESUMEN" in line or "="*15 in line:
                self.app._log_success(line)
            else:
                self.app._log_info(line)
        
        self.app.logger.log_summary(
            f"GANANCIA TOTAL (TODOS LOS PATRONES): {total_profit:.2f} $",
            f"PÉRDIDA TOTAL (TODOS LOS PATRONES): {total_loss:.2f} $"
        )
        self.app._log_success("="*75 + "\n")

    def display_strategy_summary(self, stats):
        """Formatea y muestra el resumen del análisis de estrategias en el logger."""
        if StrategyAnalyzer is None:
            return

        summary_lines, total_profit, total_loss = StrategyAnalyzer.format_strategy_summary(stats)

        for line in summary_lines:
            if "RESUMEN" in line or "="*15 in line:
                self.app._log_success(line)
            else:
                self.app._log_info(line)

        self.app.logger.log_summary(
            f"BENEFICIO TOTAL (TODAS LAS ESTRATEGIAS): {total_profit:.2f} $",
            f"PÉRDIDA TOTAL (TODAS LAS ESTRATEGIAS): {total_loss:.2f} $"
        )
        self.app._log_success("="*75 + "\n")
