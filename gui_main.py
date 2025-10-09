import os
import sys
import json
import pandas_ta as ta
import pandas as pd
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from datetime import datetime
import threading
import queue

# --- Configuración robusta de sys.path ---
# Esto asegura que el script encuentre los módulos sin importar desde dónde se ejecute.
_project_root = os.path.dirname(os.path.abspath(__file__))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    from modals.loggin_modal import LoginModal
    from modals.simulation_strategies_modal import SimulationStrategiesModal
    from loggin.loggin import LoginMT5
    from loggin.audit_log import AuditLogger # Importar la clase
    from gui.body_graphic import BodyGraphic
    from gui.body_logger import BodyLogger
    from gui.body_rsi import BodyRSI
    from gui.body_atr import BodyATR
    from gui.body_macd import BodyMACD
    from gui.body_momentum import BodyMomentum
    from backtesting.detect_candles import CandleDetector
    from backtesting.apply_strategies import StrategyAnalyzer
    from backtesting.backtesting import PerfectBacktester
    from backtesting.report_generator import ReportGenerator
    from backtesting.indicators import add_all_indicators
    from simulation.simulation import Simulation
    from main.header_builder import create_header
    from main.body_builder import create_body
    from main.preferences_manager import PreferencesManager
    from main.login_handler import LoginHandler
    from main.action_handler import ActionHandler
    from main.analysis_handler import AnalysisHandler
except Exception as e:
    # Imprimir el error de importación para facilitar la depuración
    print(f"Error al importar módulos: {e}")
    # Fallback: delayed import inside handler if needed
    LoginModal = None
    DetectAllCandlesModal = None
    DetectAllForexModal = None
    StrategySimulatorModal = None
    SimulationStrategiesModal = None
    ConfigAppModal = None
    LoginMT5 = None
    BodyGraphic = None
    BodyLogger = None
    CandleDetector = None
    StrategyAnalyzer = None
    PerfectBacktester = None
    ReportGenerator = None
    Simulation = None

# Optional: try to import MetaTrader5 to fetch symbol list after login
try:
    import MetaTrader5 as mt5
except Exception:
    mt5 = None

# Preferences file path
PREFS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_prefs.json")


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Bot Trader MT5")
        self.root.geometry("1500x1500")
        self.root.minsize(1500, 1000)
        self.root.resizable(False, False)
        self._center_on_screen(1500, 800)

        # --- Threading and Queue for background tasks ---
        self.queue = queue.Queue()
        self.thread = None

        # State for status label
        self.status_var = tk.StringVar(value="Estado: -----")

        # State for debug mode
        self.debug_mode_var = tk.BooleanVar(value=False)

        # State for aggressive mode
        self.modo_agresivo_activo = tk.BooleanVar(value=False)

        # State for chart visibility (all visible by default)
        self.show_rsi_var = tk.BooleanVar(value=True)
        self.show_atr_var = tk.BooleanVar(value=True)
        self.show_macd_var = tk.BooleanVar(value=True)
        self.show_momentum_var = tk.BooleanVar(value=True)

        # State for chart selectors (defaults)
        self.symbol_var = tk.StringVar(value="EURUSD")
        self.timeframe_var = tk.StringVar(value="M5")

        # State for simulation results
        self.initial_balance_var = tk.StringVar(value="----")
        self.equity_var = tk.StringVar(value="----")
        self.margin_var = tk.StringVar(value="----")
        self.free_margin_var = tk.StringVar(value="----")
        self.profit_var = tk.StringVar(value="----")
        self.loss_var = tk.StringVar(value="----")

        # --- Acumuladores para P/L realizado ---
        self.total_profit_realized = 0.0
        self.total_loss_realized = 0.0

        # Preferences Manager
        self.prefs_manager = PreferencesManager(self)
        self.prefs_manager.load()

        # Login Handler
        self.login_handler = LoginHandler(self)

        # Action Handler
        self.action_handler = ActionHandler(self)

        # Analysis Handler
        self.analysis_handler = AnalysisHandler(self)

        # Track whether chart has been started/shown
        self.chart_started = False

        # Instance for the simulation
        self.simulation_instance = None
        self.simulation_running = False
        self.updates_paused = False # Estado para el toggle de actualizaciones

        # Configure a simple layout: header on top, main body below
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        self._build_header()
        self._build_body()

        # Start the queue processor
        self.process_queue()

        # Ensure proper closing behavior
        self.root.protocol("WM_DELETE_WINDOW", self._on_exit)

    def _center_on_screen(self, w: int, h: int):
        self.root.update_idletasks()
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = int((screen_w / 2) - (w / 2))
        y = int((screen_h / 2) - (h / 2))
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _adjust_window_height(self):
        """Ajusta dinámicamente la altura de la ventana según las gráficas visibles."""
        base_height = 400  # Altura base (header + gráfico principal + logger)
        chart_height = 150  # Altura aproximada de cada gráfica indicadora
        
        visible_charts = 0
        if self.show_rsi_var.get():
            visible_charts += 1
        if self.show_atr_var.get():
            visible_charts += 1
        if self.show_macd_var.get():
            visible_charts += 1
        if self.show_momentum_var.get():
            visible_charts += 1
        
        total_height = base_height + (visible_charts * chart_height)
        total_height = max(800, min(total_height, 1500))  # Entre 800 y 1500 píxeles
        
        current_geometry = self.root.geometry()
        width = current_geometry.split('x')[0]
        self.root.geometry(f"{width}x{total_height}")

    def _build_header(self):
        self.header = create_header(self)

    def _build_body(self):
        self.body = create_body(self)

    def process_queue(self):
        """Procesa mensajes de la cola de hilos en el hilo principal de la GUI."""
        try:
            # Procesa todos los mensajes pendientes sin bloquear
            while not self.queue.empty():
                message_type, data = self.queue.get_nowait()

                if message_type == "log_info":
                    self._log_info(data)
                elif message_type == "log_success":
                    self._log_success(data)
                elif message_type == "log_error":
                    self._log_error(data)
                elif message_type == "status_update":
                    self._set_status(data['text'], data['color'])
                elif message_type == "login_success":
                    self._handle_login_success()
                elif message_type == "login_failure":
                    self._handle_login_failure(data)
                elif message_type == "chart_data_ready":
                    self.graphic.render_chart_data(data)
                    # Actualizar RSI con los mismos datos
                    if hasattr(self, 'rsi_chart'):
                        self.rsi_chart.update_rsi_data(data)
                    # Actualizar ATR con los mismos datos
                    if hasattr(self, 'atr_chart'):
                        self.atr_chart.update_atr_data(data)
                    # Actualizar MACD con los mismos datos
                    if hasattr(self, 'macd_chart'):
                        self.macd_chart.update_macd_data(data)
                    # Actualizar Momentum con los mismos datos
                    if hasattr(self, 'momentum_chart'):
                        self.momentum_chart.update_momentum_data(data)
                    try:
                        self.simulation_btn.state(["!disabled"])
                    except tk.TclError:
                        self.simulation_btn.configure(state="normal")
                    # Iniciar actualizaciones en vivo después de renderizar el gráfico
                    self.graphic.start_live_updates()
                elif message_type == "analysis_results":
                    self._display_analysis_summary(data['lines'], data['profit'], data['loss'])
                elif message_type == "strategy_results":
                    self._display_strategy_summary(data)
                elif message_type == "realtime_candle_update":
                    if hasattr(self, 'graphic') and self.simulation_running:
                        is_new_candle = self.graphic.update_simulation_chart(data)
                        # Actualizar RSI solo cuando se cierra una nueva vela
                        if is_new_candle and hasattr(self, 'rsi_chart') and hasattr(self.graphic, 'candles_df'):
                            self.rsi_chart.update_rsi_data(self.graphic.candles_df)
                        # Actualizar ATR solo cuando se cierra una nueva vela
                        if is_new_candle and hasattr(self, 'atr_chart') and hasattr(self.graphic, 'candles_df'):
                            self.atr_chart.update_atr_data(self.graphic.candles_df)
                        # Actualizar MACD solo cuando se cierra una nueva vela
                        if is_new_candle and hasattr(self, 'macd_chart') and hasattr(self.graphic, 'candles_df'):
                            self.macd_chart.update_macd_data(self.graphic.candles_df)
                        # Actualizar Momentum solo cuando se cierra una nueva vela
                        if is_new_candle and hasattr(self, 'momentum_chart') and hasattr(self.graphic, 'candles_df'):
                            self.momentum_chart.update_momentum_data(self.graphic.candles_df)
                elif message_type == "trade_closed":
                    self._handle_trade_closed(data)
                # Añade aquí más tipos de mensajes según sea necesario

        except queue.Empty:
            pass  # No hay nada en la cola
        finally:
            # Vuelve a programar la comprobación de la cola
            self.root.after(100, self.process_queue)

    def _start_mt5_chart(self):
        # Actualizar el balance de la cuenta desde MT5
        if mt5:
            try:
                # Verificar si hay una conexión activa
                if mt5.terminal_info():
                    account_info = mt5.account_info()
                    if account_info:
                        balance = account_info.balance
                        # Formatear como string con 2 decimales y símbolo de dólar
                        self.initial_balance_var.set(f"{balance:.2f} $")
                        self._log_info(f"Balance de cuenta actualizado: {balance:.2f} $")
                    else:
                        self._log_error("No se pudo obtener la información de la cuenta.")
                else:
                    # Este caso es poco probable si el botón está activo, pero es una buena práctica
                    self._log_error("No hay conexión con MT5 para actualizar el balance.")
            except Exception as e:
                self._log_error(f"Error al obtener el balance de MT5: {e}")

        # Show the chart and load data for current selection
        if not self.chart_started:
            # Replace placeholder with the actual chart frame
            try:
                self.graphic_placeholder.grid_forget()
            except Exception:
                pass
            try:
                self.graphic.grid(row=0, column=0, sticky="nsew")
            except Exception:
                pass
            self.chart_started = True
        # Load/refresh with selected symbol/timeframe
        self._log_info(f"Inicializando gráfico para {self.symbol_var.get()} ({self.timeframe_var.get()})…")
        try:
            if hasattr(self, "graphic") and hasattr(self.graphic, "load_symbol"):
                # Cargar datos en un hilo para no bloquear la UI
                self.graphic.load_symbol(
                    symbol=self.symbol_var.get(), 
                    timeframe=self.timeframe_var.get(),
                    queue=self.queue
                )
        except Exception as e:
            self._log_error(f"No se pudo iniciar el gráfico: {e})")

    def _open_login_modal(self):
        self.login_handler.open_login_modal()

    def _attempt_login(self, creds: dict):
        """Inicia el proceso de login en un hilo secundario para no bloquear la GUI."""
        self._set_status("Conectando...", "orange")
        self._log_info(f"Intentando conexión a MT5 con cuenta {creds.get('cuenta')}...")

        # Crear y empezar el hilo para la tarea de login
        self.thread = threading.Thread(target=self._login_worker, args=(creds,), daemon=True)
        self.thread.start()

    def _login_worker(self, creds: dict):
        """Esta función se ejecuta en un hilo separado para manejar la conexión bloqueante."""
        global LoginMT5
        if LoginMT5 is None:
            try:
                from loggin.loggin import LoginMT5 as LM5
                LoginMT5 = LM5
            except Exception as e:
                self.queue.put(("login_failure", {"error": f"No se pudo importar LoginMT5: {e}"}))
                return

        try:
            client = LoginMT5(
                account=creds.get("cuenta"),
                password=creds.get("contraseña"),
                server=creds.get("servidor")
            )

            connected = client.login()
            if connected:
                self.queue.put(("login_success", None))
            else:
                self.queue.put(("login_failure", {"error": "Credenciales incorrectas o terminal no disponible."}))

        except Exception as e:
            self.queue.put(("login_failure", {"error": f"Excepción durante la conexión: {e}"}))

    def _handle_login_success(self):
        """Maneja las actualizaciones de la GUI después de un login exitoso."""
        self._set_status("Conectado", "green")
        self._log_success("Conexión establecida correctamente.")
        self._populate_symbols()
        try:
            self.start_btn.state(["!disabled"])
            self.symbol_cb.state(["!disabled"])
            self.timeframe_cb.state(["!disabled"])
        except tk.TclError:
            self.start_btn.configure(state="normal")
            self.symbol_cb.configure(state="normal")
            self.timeframe_cb.configure(state="normal")

        if self.chart_started:
            self._apply_chart_selection()

    def _handle_login_failure(self, data):
        """Maneja las actualizaciones de la GUI después de un login fallido."""
        error_msg = data.get('error', 'Error desconocido')
        messagebox.showerror("Error de conexión", f"No se pudo conectar a MT5: {error_msg}")
        self._set_status("Error de conexión", "red")
        self._log_error(f"Fallo en la conexión: {error_msg}")

    def _populate_symbols(self):
        if mt5 is None:
            return
        try:
            symbols = mt5.symbols_get()
            if not symbols:
                return

            def _is_forex(sym):
                try:
                    name = getattr(sym, "name", "") or ""
                    path = (getattr(sym, "path", "") or "").lower()
                    cb = getattr(sym, "currency_base", "") or ""
                    cp = getattr(sym, "currency_profit", "") or ""
                    # Heuristics:
                    cond_path = "forex" in path  
                    up = name.upper()
                    cond_name = up.isalpha() and len(up) == 6  
                    cond_curr = len(cb) == 3 and len(cp) == 3 and cb.isalpha() and cp.isalpha()
                    return cond_path or (cond_name and cond_curr)
                except Exception:
                    return False

            forex_syms = [s for s in symbols if _is_forex(s)]
            if not forex_syms:
                return

            visibles = [s.name for s in forex_syms if getattr(s, "visible", False)]
            if not visibles:
                visibles = [s.name for s in forex_syms]

            # Common FX at top, then the rest sorted
            commons = [
                "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD",
                "EURJPY", "EURGBP", "EURCHF", "GBPJPY",
            ]
            ordered_unique = list(dict.fromkeys(commons + sorted(set(visibles))))
            self.symbol_cb.configure(values=ordered_unique)

            # If current selection not present, set to first common available
            current = self.symbol_var.get()
            if current not in ordered_unique:
                for c in commons:
                    if c in ordered_unique:
                        self.symbol_var.set(c)
                        break
                else:
                    self.symbol_var.set(ordered_unique[0])
        except Exception:
            pass

    def _apply_chart_selection(self, event=None):
        symbol = self.symbol_var.get().strip()
        timeframe = self.timeframe_var.get().strip()
        # Save selection to preferences
        self.prefs_manager.save(symbol=symbol, timeframe=timeframe)
        # Only update the chart if it has been started
        if self.chart_started and symbol and hasattr(self, "graphic") and hasattr(self.graphic, "load_symbol"):
            self._log_info(f"Cambiando gráfico a {symbol} ({timeframe})")
            try:
                self.graphic.load_symbol(
                    symbol=symbol, 
                    timeframe=timeframe, 
                    queue=self.queue
                )
            except Exception as e:
                self._log_error(f"No se pudo actualizar el gráfico: {e}")

    def _load_prefs(self):
        try:
            if os.path.exists(PREFS_PATH):
                with open(PREFS_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                sym = data.get("symbol")
                tf = data.get("timeframe")
                if isinstance(sym, str) and sym:
                    self.symbol_var.set(sym)
                if isinstance(tf, str) and tf:
                    self.timeframe_var.set(tf)
        except Exception:
            # Ignore malformed json
            pass

    def _save_prefs(self, symbol: str = None, timeframe: str = None):
        try:
            data = {}
            if os.path.exists(PREFS_PATH):
                try:
                    with open(PREFS_PATH, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    data = {}
            if symbol is not None:
                data["symbol"] = symbol
            if timeframe is not None:
                data["timeframe"] = timeframe
            with open(PREFS_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            # Do not block UI on save errors
            pass

    def _set_status(self, text: str, color: str):
        self.status_var.set(f"Estado: {text}")
        try:
            self.status_label.configure(foreground=color)
        except tk.TclError:
            # Fallback in case theme doesn't support foreground on ttk.Label
            self.status_label = tk.Label(self.status_label.master, textvariable=self.status_var, fg=color)
            self.status_label.grid(row=0, column=7, padx=(12, 12))

    def _log_info(self, msg: str):
        if hasattr(self, "logger") and hasattr(self.logger, "log"):
            self.logger.log(msg)

    def _log_custom(self, msg: str, color: str):
        """Registra un mensaje con un color personalizado."""
        if hasattr(self, "logger") and hasattr(self.logger, "log"):
            self.logger.log(msg, color=color)

    def _log_success(self, msg: str):
        if hasattr(self, "logger") and hasattr(self.logger, "success"):
            self.logger.success(msg)

    def _log_error(self, msg: str):
        if hasattr(self, "logger") and hasattr(self.logger, "error"):
            self.logger.error(msg)

    def _open_detect_candle_modal(self):
        self.action_handler.open_detect_candle_modal()

    def _open_detect_forex_modal(self):
        self.action_handler.open_detect_forex_modal()

    def _apply_strategies_action(self):
        self.action_handler.apply_strategies_action()

    def _run_pattern_analysis(self, selected_patterns):
        """Ejecuta el análisis de patrones y muestra los resultados."""
        self.analysis_handler.run_pattern_analysis(selected_patterns)

    def _run_strategy_analysis(self, selected_strategies):
        """Ejecuta el análisis de estrategias y muestra los resultados."""
        self.analysis_handler.run_strategy_analysis(selected_strategies)

    def _add_technical_indicators(self, df):
        """Añade una serie de indicadores técnicos al DataFrame."""
        if df is None or df.empty:
            return df

        # Copia para evitar SettingWithCopyWarning
        df = df.copy()

        try:
            # Medias Móviles Exponenciales (EMA)
            df.ta.ema(length=12, append=True, col_names=('ema_fast',))
            df.ta.ema(length=26, append=True, col_names=('ema_slow',))
            df.ta.ema(length=50, append=True, col_names=('ema_50',))
            df.ta.ema(length=200, append=True, col_names=('ema_200',))

            # RSI
            df.ta.rsi(length=14, append=True, col_names=('rsi',))

            # MACD
            macd = df.ta.macd(fast=12, slow=26, signal=9)
            if macd is not None and not macd.empty:
                df['macd_line'] = macd.iloc[:, 0]
                df['macd_signal'] = macd.iloc[:, 2]

            # Bandas de Bollinger
            bbands = df.ta.bbands(length=20, std=2)
            if bbands is not None and not bbands.empty:
                df['bb_lower'] = bbands.iloc[:, 0]
                df['bb_upper'] = bbands.iloc[:, 2]

            # Ichimoku Cloud
            ichimoku_tuple = df.ta.ichimoku(tenkan=9, kijun=26, senkou=52)
            # Ichimoku devuelve una tupla de DataFrames
            if ichimoku_tuple and ichimoku_tuple[0] is not None and not ichimoku_tuple[0].empty:
                ichimoku_df = ichimoku_tuple[0]
                df['tenkan_sen'] = ichimoku_df[f'ITS_9']
                df['kijun_sen'] = ichimoku_df[f'IKS_26']
                df['senkou_span_a'] = ichimoku_df[f'ISA_9']
                df['senkou_span_b'] = ichimoku_df[f'ISB_26']

            # StochRSI
            stoch_rsi = df.ta.stochrsi(length=14, rsi_length=14, k=3, d=3)
            if stoch_rsi is not None and not stoch_rsi.empty:
                df['stochrsi_k'] = stoch_rsi.iloc[:, 0]

            # ATR
            df.ta.atr(length=14, append=True, col_names=('atr',))

            self._log_info("Indicadores técnicos calculados correctamente.")

        except Exception as e:
            self._log_error(f"Error al calcular indicadores técnicos: {e}")
        
        return df

    def _run_perfect_backtesting(self):
        """Ejecuta un backtesting 'perfecto' y muestra los resultados."""
        if not self.chart_started or not hasattr(self.graphic, 'candles_df') or self.graphic.candles_df is None:
            self._log_error("El gráfico no está iniciado o no hay datos de velas disponibles.")
            return

        if PerfectBacktester is None:
            self._log_error("El módulo de backtesting no está disponible.")
            return

        try:
            self._log_info("Iniciando backtesting perfecto... Esto puede tardar un momento.")
            # Crear una copia para asegurar la consistencia de los nombres de columna
            candles_df_copy = self.graphic.candles_df.copy()
            candles_df_copy.columns = [col.lower() for col in candles_df_copy.columns]

            # --- AÑADIR INDICADORES TÉCNICOS ---
            candles_df_copy = self._add_technical_indicators(candles_df_copy)

            # Recargar la configuración del logger de auditoría antes de ejecutar
            AuditLogger()._load_config()
            AuditLogger()._setup_log_file()

            backtester = PerfectBacktester(candles_df_copy, symbol=self.symbol_var.get())
            stats, profitable_trades, signal_names, all_generated_signals = backtester.run()
            
            # Registrar todas las señales evaluadas
            self._log_info("-"*50)
            self._log_info("Señales evaluadas en este backtest:")
            for signal_name in sorted(signal_names):
                clean_name = signal_name.replace('strategy_', '').replace('pattern_', '').replace('_', ' ').title()
                signal_type = "[forex]" if signal_name.startswith('strategy_') else "[candle]"
                self._log_info(f"- {clean_name} {signal_type}")

            # Registrar todas las señales generadas (rentables o no)
            self._log_info("-"*50)
            self._log_info("Señales generadas (rentables o no):")
            from collections import Counter
            signal_counts = Counter(s['name'] for s in all_generated_signals)
            
            # Mostrar todas las señales evaluadas, con su contador (o 0 si no se generaron)
            for signal_name in sorted(signal_names):
                count = signal_counts.get(signal_name, 0)
                clean_name = signal_name.replace('strategy_', '').replace('pattern_', '').replace('_', ' ').title()
                self._log_info(f"- {clean_name}: {count} veces")

            summary_lines, total_profit = PerfectBacktester.format_summary(stats)

            # Dibujar las operaciones en el gráfico
            if hasattr(self, 'graphic') and hasattr(self.graphic, 'draw_trades'):
                self.graphic.draw_trades(profitable_trades)

            # Imprimir resumen en el logger
            for line in summary_lines:
                self._log_info(line)
            self._log_success(f"BENEFICIO TOTAL PERFECTO: {total_profit:.2f} $")
            self._log_info("="*85)

            # Generar y guardar el informe detallado
            report_generator = ReportGenerator(
                profitable_trades=profitable_trades,
                summary_lines=summary_lines,
                total_profit=total_profit,
                symbol=self.graphic.symbol,
                timeframe=self.graphic.timeframe
            )
            report_path = report_generator.generate_report()
            if report_path:
                self._log_success(f"Informe detallado guardado en: {report_path}")
            else:
                self._log_error("No se pudo generar el informe detallado.")

        except Exception as e:
            self._log_error(f"Ocurrió un error durante el backtesting: {e}")
            # Opcional: imprimir traceback para depuración
            import traceback
            traceback.print_exc()

    def _finalize_backtesting_action(self):
        """Limpia los dibujos del gráfico y el contenido del logger."""
        if hasattr(self, 'graphic') and hasattr(self.graphic, 'clear_drawings'):
            self.graphic.clear_drawings()
            self._log_info("Dibujos del gráfico eliminados.")
        self._clear_log_action()

    def _modo_agresivo_action(self):
        """Activa/desactiva el modo agresivo."""
        # El estado se gestiona a través del Checkbutton y self.modo_agresivo_activo.
        # Esta función se llama cuando el usuario hace clic, así que solo registramos el estado.
        is_active = self.modo_agresivo_activo.get()
        if is_active:
            self._log_custom("Modo Agresivo ACTIVADO. Las próximas simulaciones usarán parámetros de mayor riesgo.", "#FF8C00")
        else:
            self._log_info("Modo Agresivo DESACTIVADO. Las próximas simulaciones usarán la configuración estándar.")

    def _aplicar_config_agresiva(self, config):
        """Modifica la configuración de estrategias para hacerla más agresiva."""
        self._log_info("Aplicando transformación de configuración a MODO AGRESIVO.")
        new_config = config.copy() # Trabajar sobre una copia

        # --- Modificar Riesgo Global ---
        # Aumentar el riesgo por operación a un 0.5% del equity
        if 'general' not in new_config:
            new_config['general'] = {}
        new_config['general']['risk_per_trade_percent'] = "0.5"
        self._log_custom("  - Riesgo por operación aumentado a 0.5%", "#FF8C00")

        # --- Modificar Estrategias Forex ---
        if 'forex_strategies' in new_config:
            for strategy_name, params in new_config['forex_strategies'].items():
                if params.get('selected'):
                    # Aumentar la relación riesgo/beneficio (más Take Profit)
                    params['rr_ratio'] = 3.0
                    # Reducir el Stop Loss para mejorar la relación R/R
                    params['stop_loss_pips'] = 15.0
                    self._log_custom(f"  - Estrategia Forex '{strategy_name}': RR Ratio -> 3.0, SL Pips -> 15.0", "#FF8C00")

        return new_config

    def _iniciar_simulacion_action(self):
        """Abre el modal de configuración y, si se acepta, inicia la simulación."""
        if not self.chart_started or not hasattr(self.graphic, 'candles_df') or self.graphic.candles_df.empty:
            messagebox.showerror("Error de Simulación", "No hay datos de gráfico cargados. Inicie el gráfico antes de simular.")
            return

        if self.simulation_instance:
            messagebox.showinfo("Información", "Ya hay una simulación en curso. Deténgala para iniciar una nueva.")
            return
        
        # Abrir el modal para que el usuario configure las estrategias
        modal = SimulationStrategiesModal(self.root, candles_df=self.graphic.candles_df, logger=self.logger)
        self.root.wait_window(modal)

        # Solo iniciar la simulación si el usuario guardó la configuración en el modal
        if hasattr(modal, 'result') and modal.result:
            strategies_config = modal.result

            # --- APLICAR MODO AGRESIVO SI ESTÁ ACTIVO ---
            if self.modo_agresivo_activo.get():
                strategies_config = self._aplicar_config_agresiva(strategies_config)
            # --------------------------------------------

            self._log_success("Configuración de estrategias aceptada. Iniciando simulación...")

            try:
                balance_str = self.initial_balance_var.get().replace('$', '').strip()
                initial_balance = float(balance_str) if balance_str != '----' else 10000.0

                self.simulation_instance = Simulation(
                    initial_balance=initial_balance,
                    symbol=self.symbol_var.get(),
                    timeframe=self.timeframe_var.get(),
                    strategies_config=strategies_config,
                    logger=self.logger,
                    on_candle_update_callback=self.graphic.update_realtime_candle,
                    debug_mode=self.debug_mode_var.get()
                )
                
                self.simulation_running = True
                self._start_simulation_loop()
                self._log_success(f"Simulación iniciada para {self.symbol_var.get()} con un balance de {initial_balance:.2f} $.")

                # Habilitar el control del modo agresivo, sin activarlo por defecto
                self.simulation_menu.entryconfig("Modo agresivo", state="normal")
                # Habilitar botones de gestión de operaciones
                self.simulation_menu.entryconfig("Ver operaciones abiertas", state="normal")
                self.simulation_menu.entryconfig("Cerrar operaciones", state="normal") 
                self.simulation_menu.entryconfig("Detener simulación", state="normal")

            except Exception as e:
                self._log_error(f"Error al iniciar la simulación: {e}")
                messagebox.showerror("Error", f"No se pudo iniciar la simulación: {e}")
        else:
            self._log_info("Inicio de simulación cancelado por el usuario.")

    def _detener_simulacion_action(self):
        """Detiene la simulación, cierra todas las operaciones y guarda el log."""
        if not self.simulation_instance:
            messagebox.showinfo("Información", "No hay ninguna simulación en curso.")
            return

        if not self.simulation_running:
            messagebox.showinfo("Información", "La simulación no está en ejecución.")
            return

        self._log_info("Deteniendo simulación...")

        try:
            # Indicar a la simulación que se detenga
            self.simulation_running = False

            # Deshabilitar y resetear el modo agresivo
            self.simulation_menu.entryconfig("Modo agresivo", state="disabled")
            if self.modo_agresivo_activo.get():
                self.modo_agresivo_activo.set(False)
                self._log_info("Modo Agresivo DESACTIVADO al detener la simulación.")

            # Deshabilitar botones de gestión de operaciones
            self.simulation_menu.entryconfig("Ver operaciones abiertas", state="disabled")
            self.simulation_menu.entryconfig("Cerrar operaciones", state="disabled") 
            self.simulation_menu.entryconfig("Detener simulación", state="disabled")

            # Reactivar las actualizaciones en vivo del gráfico
            if hasattr(self, 'graphic'):
                self.graphic.refresh() # Recargamos el gráfico para mostrar el estado final real

            # Cerrar todas las posiciones abiertas para el símbolo actual
            try:
                open_positions = mt5.positions_get(symbol=self.simulation_instance.symbol)
                if open_positions and len(open_positions) > 0:
                    self._log_info(f"Cerrando {len(open_positions)} posiciones abiertas para {self.simulation_instance.symbol}...")
                    for pos in open_positions:
                        trade_type = 'long' if pos.type == mt5.POSITION_TYPE_BUY else 'short'
                        self.simulation_instance.close_trade(pos.ticket, pos.volume, trade_type)
                else:
                    self._log_info("No hay posiciones abiertas para cerrar.")
            except Exception as e:
                self._log_error(f"Error al intentar cerrar posiciones abiertas: {e}")

            # Guardar el log de la sesión
            self.action_handler.save_session_log()

            self.simulation_instance = None
            self._log_success("Simulación detenida y operaciones cerradas.")

            # Actualizar y limpiar las etiquetas de la UI
            try:
                account_info = mt5.account_info()
                if account_info:
                    self.initial_balance_var.set(f"{account_info.balance:.2f} $")
                    self.equity_var.set(f"{account_info.equity:.2f} $")
                    self.margin_var.set("0.00 $")
                    self.free_margin_var.set(f"{account_info.margin_free:.2f} $")
            finally:
                # Limpiar labels de profit/loss ya que no hay simulación activa
                self.profit_var.set("----")
                self.loss_var.set("----")

        except Exception as e:
            self._log_error(f"Error al detener la simulación: {e}")

    def _toggle_debug_mode_action(self):
        """
        Activa o desactiva el modo debug en la simulación activa.
        """
        is_debug = self.debug_mode_var.get()
        
        # Si la simulación está corriendo, actualiza la instancia en tiempo real
        if hasattr(self, 'simulation_instance') and self.simulation_instance:
            self.simulation_instance.set_debug_mode(is_debug)
        else:
            # Si no, solo loguea el cambio de estado para la próxima simulación
            status = "activado" if is_debug else "desactivado"

    def _ver_operaciones_abiertas_action(self):
        """Muestra las operaciones abiertas en una ventana modal no bloqueante."""
        if not self.simulation_instance:
            messagebox.showinfo("Información", "No hay ninguna simulación en curso.")
            return

        if not self.simulation_running:
            messagebox.showinfo("Información", "La simulación no está en ejecución.")
            return

        try:
            # Importar la ventana de operaciones abiertas
            from operations.window_operations import OperacionesAbiertasWindow
            
            # Crear y mostrar la ventana modal no bloqueante
            operations_window = OperacionesAbiertasWindow(
                parent=self.root,
                simulation_instance=self.simulation_instance,
                logger=self.logger,
                app=self  # Añadir referencia a la app
            )
            
            if self.debug_mode_var.get():
                self._log_info("Ventana de operaciones abiertas abierta")
            
        except ImportError as e:
            self._log_error(f"Error al importar ventana de operaciones: {e}")
            messagebox.showerror("Error", "No se pudo abrir la ventana de operaciones abiertas")

        except Exception as e:
            self._log_error(f"Error al abrir ventana de operaciones: {e}")
            messagebox.showerror("Error", f"Error inesperado: {e}")

    def _cerrar_operaciones_action(self):
        """Abre ventana modal para gestionar operaciones abiertas."""
        if not self.simulation_instance:
            messagebox.showinfo("Información", "No hay ninguna simulación en curso.")
            return

        if not self.simulation_running:
            messagebox.showinfo("Información", "La simulación no está en ejecución.")
            return

        try:
            from operations.window_close_operations import CerrarOperacionesWindow
            
            operations_window = CerrarOperacionesWindow(
                parent=self.root,
                simulation_instance=self.simulation_instance,
                logger=self.logger
            )
            
            if self.debug_mode_var.get():
                self._log_info("Ventana de gestión de operaciones abierta")
            
        except ImportError as e:
            self._log_error(f"Error al importar ventana de gestión: {e}")
            messagebox.showerror("Error", "No se pudo abrir la ventana de gestión de operaciones")
        except Exception as e:
            self._log_error(f"Error al abrir ventana de gestión: {e}")
            messagebox.showerror("Error", f"Error inesperado: {e}")

    def _detener_actualizacion_action(self):
        """Pausa o reanuda las actualizaciones del gráfico y del balance."""
        if not self.updates_paused:
            # --- PAUSAR ACTUALIZACIONES ---
            self.updates_paused = True
            self._log_info("Pausando actualizaciones en tiempo real...")

            # Detener bucles de actualización
            self.simulation_running = False
            if hasattr(self, 'graphic'):
                self.graphic._stop_live_updates()

            # Cambiar texto del menú y habilitar herramientas
            self.simulation_menu.entryconfig("Pausar", label="Reanudar")
            self.analysis_tools_btn.state(["!disabled"])
            self.analysis_tools_btn.update_idletasks()
            self._log_success("Actualizaciones pausadas. Herramientas de análisis habilitadas.")

            # Si hay una simulación, detenerla
            if self.simulation_instance:
                self._detener_simulacion_action()
        else:
            # --- REANUDAR ACTUALIZACIONES ---
            self.updates_paused = False
            self._log_info("Reanudando actualizaciones en tiempo real...")

            # Cambiar texto del menú y deshabilitar herramientas
            self.simulation_menu.entryconfig("Reanudar", label="Pausar")
            self.analysis_tools_btn.state(["disabled"])
            self.analysis_tools_btn.update_idletasks()

            # Refrescar el gráfico para obtener los datos perdidos
            if hasattr(self, 'graphic'):
                self.graphic.refresh()
                # Las actualizaciones en vivo se reinician automáticamente después de 'refresh' a través de la cola

            self._log_success("Actualizaciones reanudadas. Herramientas de análisis deshabilitadas.")

    def _start_simulation_loop(self):
        """Bucle principal que se ejecuta cada segundo para actualizar la simulación."""
        if not self.simulation_running or not self.simulation_instance or not mt5 or not mt5.terminal_info():
            if self.simulation_running:
                self._log_error("Se perdió la conexión con MT5 o la simulación se detuvo. Bucle finalizado.")
                self.simulation_running = False 
            return

        try:
            # 1. Obtener el precio actual
            symbol = self.simulation_instance.symbol
            tick = mt5.symbol_info_tick(symbol)
            if tick:
                # Usar el precio medio para on_tick, ya que es para la formación de velas
                price = (tick.bid + tick.ask) / 2
                timestamp = pd.to_datetime(tick.time, unit='s')
                
                # 2. Procesar el tick en la simulación (esto formará velas y ejecutará estrategias)
                self.simulation_instance.on_tick(timestamp, price)

            # 3. Obtener y actualizar el resumen de la cuenta desde MT5
            summary = self.simulation_instance.get_account_summary()
            if summary:
                self.equity_var.set(f"{summary['equity']:.2f} $")
                self.margin_var.set(f"{summary['margin']:.2f} $")
                self.free_margin_var.set(f"{summary['free_margin']:.2f} $")
                
                # El 'profit' de account_info es el P/L flotante
                profit_or_loss = summary.get('profit', 0.0)
                if profit_or_loss >= 0:
                    self.profit_var.set(f"{profit_or_loss:.2f} $")
                    self.loss_var.set("0.00 $")
                else:
                    self.profit_var.set("0.00 $")
                    self.loss_var.set(f"{abs(profit_or_loss):.2f} $")

        except Exception as e:
            self._log_error(f"Error en el bucle de simulación: {e}")

        # Programar la siguiente ejecución si la simulación sigue activa
        if self.simulation_running:
            self.root.after(1000, self._start_simulation_loop)

    def _clear_log_action(self):
        """Limpia el contenido del logger.""" 
        self.action_handler.clear_log()

    def _on_exit(self):
        """Maneja el cierre de la aplicación de forma segura."""
        self.action_handler.on_exit()

    def _save_chart_to_csv(self):
        """Guarda los datos actuales del gráfico en un archivo CSV."""
        self.action_handler.save_chart_to_csv()

    def _handle_trade_closed(self, data):
        """Actualiza los contadores de P/L acumulado cuando se cierra una operación."""
        profit = data.get('profit', 0.0)
        if profit >= 0:
            self.total_profit_realized += profit
            self.profit_var.set(f"{self.total_profit_realized:.2f} $")
        else:
            # Las pérdidas se suman como valores positivos
            self.total_loss_realized += abs(profit)
            self.loss_var.set(f"{self.total_loss_realized:.2f} $")


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()