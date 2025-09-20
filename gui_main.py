import os
import sys
import json
import pandas_ta as ta
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

# --- Configuración robusta de sys.path ---
# Esto asegura que el script encuentre los módulos sin importar desde dónde se ejecute.
_project_root = os.path.dirname(os.path.abspath(__file__))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    from modals.loggin_modal import LoginModal
    from modals.detect_all_candles_modal import DetectAllCandlesModal
    from modals.detect_all_forex_modal import DetectAllForexModal
    from modals.strategy_simulator_modal import StrategySimulatorModal
    from loggin.loggin import LoginMT5
    from gui.body_graphic import BodyGraphic
    from gui.body_logger import BodyLogger
    from backtesting.detect_candles import CandleDetector
    from backtesting.apply_strategies import StrategyAnalyzer
    from backtesting.backtesting import PerfectBacktester
except Exception as e:
    # Imprimir el error de importación para facilitar la depuración
    print(f"Error al importar módulos: {e}")
    # Fallback: delayed import inside handler if needed
    LoginModal = None
    DetectAllCandlesModal = None
    DetectAllForexModal = None
    StrategySimulatorModal = None
    LoginMT5 = None
    BodyGraphic = None
    BodyLogger = None
    CandleDetector = None
    StrategyAnalyzer = None
    PerfectBacktester = None

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
        self.root.geometry("1500x800")
        self.root.minsize(900, 600)
        self.root.resizable(False, False)
        self._center_on_screen(1500, 800)

        # State for status label
        self.status_var = tk.StringVar(value="Estado: -----")

        # State for debug mode
        self.debug_mode_var = tk.BooleanVar(value=False)

        # State for chart selectors (defaults)
        self.symbol_var = tk.StringVar(value="EURUSD")
        self.timeframe_var = tk.StringVar(value="M5")

        # State for simulation results
        self.initial_balance_var = tk.StringVar(value="----")
        self.profit_var = tk.StringVar(value="----")
        self.loss_var = tk.StringVar(value="----")

        # Load persisted preferences (overrides defaults)
        self._load_prefs()

        # Track whether chart has been started/shown
        self.chart_started = False

        # Configure a simple layout: header on top, main body below
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        self._build_header()
        self._build_body()

        # Ensure proper closing behavior
        self.root.protocol("WM_DELETE_WINDOW", self._on_exit)

    def _center_on_screen(self, w: int, h: int):
        self.root.update_idletasks()
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = int((screen_w / 2) - (w / 2))
        y = int((screen_h / 2) - (h / 2))
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _build_header(self):
        header = ttk.Frame(self.root, padding=(16, 10))
        header.grid(row=0, column=0, sticky="ew")

        # --- Botón de Herramientas de Análisis (Columna 0) ---
        self.analysis_tools_btn = ttk.Menubutton(header, text="Herramientas")
        self.analysis_tools_btn.grid(row=0, column=0, padx=(6, 12))
        tools_menu = tk.Menu(self.analysis_tools_btn, tearoff=False)
        self.analysis_tools_btn["menu"] = tools_menu
        tools_menu.add_command(label="Aplicar estrategias", command=self._apply_strategies_action)
        tools_menu.add_command(label="Detectar patrones de velas", command=self._open_detect_candle_modal)
        tools_menu.add_command(label="Detectar Estrategias forex", command=self._open_detect_forex_modal)
        tools_menu.add_separator()
        tools_menu.add_command(label="Iniciar Backtesting", command=self._run_perfect_backtesting)
        tools_menu.add_command(label="Finalizar backtesting", command=self._finalize_backtesting_action)
        tools_menu.add_command(label="Limpiar log", command=self._clear_log_action)
        self.analysis_tools_btn.state(["disabled"])

        # --- Menú de Opciones (Columna 1) ---
        self.options_btn = ttk.Menubutton(header, text="Opciones")
        self.options_btn.grid(row=0, column=1, padx=(10, 0))
        options_menu = tk.Menu(self.options_btn, tearoff=False)
        self.options_btn["menu"] = options_menu
        options_menu.add_checkbutton(label="Modo Debug (Log de Precios)", variable=self.debug_mode_var)

        # --- Botón de Simulación (Columna 2) ---
        self.simulation_btn = ttk.Menubutton(header, text="Simulación")
        self.simulation_btn.grid(row=0, column=2, padx=(10, 0)) # 10px de separación a la izquierda
        simulation_menu = tk.Menu(self.simulation_btn, tearoff=False)
        self.simulation_btn["menu"] = simulation_menu
        simulation_menu.add_command(label="Iniciar simulación", command=self._iniciar_simulacion_action)
        simulation_menu.add_command(label="Abrir operación manual", command=self._abrir_operacion_manual_action)
        simulation_menu.add_command(label="Modificar estrategias", command=self._modificar_estrategias_action)
        simulation_menu.add_separator()
        simulation_menu.add_command(label="Cancelar simulación", command=self._cancelar_simulacion_action)
        self.simulation_btn.state(["disabled"])

        # --- Labels for Simulation Results (Columna 3) ---
        results_frame = ttk.Frame(header, padding=(10, 0))
        results_frame.grid(row=0, column=3, sticky="ew", padx=(10, 0))

        ttk.Label(results_frame, text="Dinero inicial:").pack(side="left", padx=(0, 5))
        ttk.Label(results_frame, textvariable=self.initial_balance_var, foreground="black").pack(side="left", padx=(0, 10))

        ttk.Label(results_frame, text="Beneficios:").pack(side="left", padx=(0, 5))
        ttk.Label(results_frame, textvariable=self.profit_var, foreground="green").pack(side="left", padx=(0, 10))

        ttk.Label(results_frame, text="Pérdidas:").pack(side="left", padx=(0, 5))
        ttk.Label(results_frame, textvariable=self.loss_var, foreground="red").pack(side="left")

        # Spacer para empujar los controles a la derecha (Columna 4)
        spacer = ttk.Frame(header)
        spacer.grid(row=0, column=4, sticky="ew")

        # El resto de los controles (desde la Columna 5 en adelante)
        ttk.Label(header, text="Símbolo:").grid(row=0, column=5, padx=(0, 6))
        self.symbol_cb = ttk.Combobox(header, textvariable=self.symbol_var, width=12, state="disabled")
        self.symbol_cb["values"] = ("EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "BTCUSD")
        self.symbol_cb.grid(row=0, column=6)
        self.symbol_cb.bind("<<ComboboxSelected>>", self._apply_chart_selection)

        ttk.Label(header, text="Timeframe:").grid(row=0, column=7, padx=(12, 6))
        self.timeframe_cb = ttk.Combobox(header, textvariable=self.timeframe_var, width=8, state="disabled")
        self.timeframe_cb["values"] = ("M1", "M5", "M15", "M30", "H1", "H4", "D1")
        self.timeframe_cb.grid(row=0, column=8)
        self.timeframe_cb.bind("<<ComboboxSelected>>", self._apply_chart_selection)

        self.start_btn = ttk.Button(header, text="Iniciar MT5", command=self._start_mt5_chart)
        self.start_btn.grid(row=0, column=9, padx=(12, 12))
        self.start_btn.state(["disabled"])

        self.status_label = ttk.Label(header, textvariable=self.status_var, foreground="black")
        self.status_label.grid(row=0, column=10, padx=(12, 12))

        conectar_btn = ttk.Button(header, text="Conectar", command=self._open_login_modal)
        conectar_btn.grid(row=0, column=11, padx=(6, 12))

        # Configuración de las columnas del header
        header.columnconfigure(4, weight=1)  # El spacer (col 4) se expande

    def _build_body(self):
        container = ttk.Frame(self.root, padding=(12, 10))
        container.grid(row=1, column=0, sticky="nsew")
        container.columnconfigure(0, weight=1)
        # Split rows: top chart (3x), bottom logger (1x)
        container.rowconfigure(0, weight=3)
        container.rowconfigure(1, weight=1)

        # Bottom: Logger (create it first)
        if BodyLogger is None:
            self.logger = ttk.Frame(container)
            ttk.Label(self.logger, text="Logger no disponible").pack(expand=True, fill="both")
        else:
            self.logger = BodyLogger(container)
        self.logger.grid(row=1, column=0, sticky="nsew", pady=(10, 0))

        # Top: Graphic placeholder (shown until Start MT5 is pressed)
        self.graphic_placeholder = ttk.Frame(container)
        self.graphic_placeholder.grid(row=0, column=0, sticky="nsew")
        placeholder_lbl = ttk.Label(
            self.graphic_placeholder,
            text="Pulsa 'Iniciar MT5' para cargar el gráfico",
            anchor="center",
            font=("Segoe UI", 12),
            foreground="#555",
        )
        placeholder_lbl.pack(expand=True, fill="both")

        # Prepare the graphic but do not show it yet
        if BodyGraphic is None:
            self.graphic = ttk.Frame(container)
            ttk.Label(self.graphic, text="Gráfico no disponible").pack(expand=True, fill="both")
        else:
            # Pass the logger to the graphic
            self.graphic = BodyGraphic(
                container, 
                symbol=self.symbol_var.get(), 
                timeframe=self.timeframe_var.get(), 
                bars=300,
                logger=self.logger,  # Pass logger instance
                debug_mode_var=self.debug_mode_var # Pass debug mode variable
            )
        # Do not grid the graphic now; it will be gridded when started

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
                self.graphic.load_symbol(symbol=self.symbol_var.get(), timeframe=self.timeframe_var.get())
        except Exception as e:
            self._log_error(f"No se pudo iniciar el gráfico: {e}")
        try:
            self.analysis_tools_btn.state(["!disabled"])
            self.simulation_btn.state(["!disabled"])
        except Exception:
            self.analysis_tools_btn.configure(state="normal")
            self.simulation_btn.configure(state="normal")

    def _open_login_modal(self):
        global LoginModal, LoginMT5
        if LoginModal is None:
            try:
                from modals.loggin_modal import LoginModal as LM
                LoginModal = LM
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo abrir el modal: {e}")
                return

        # Open modal and wait for result
        modal = LoginModal(self.root)
        self.root.wait_window(modal)
        result = getattr(modal, "result", None)

        if result:
            self._attempt_login(result)

    def _attempt_login(self, creds: dict):
        global LoginMT5
        if LoginMT5 is None:
            try:
                from loggin.loggin import LoginMT5 as LM5
                LoginMT5 = LM5
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo importar LoginMT5: {e}")
                self._set_status("Desconectado", "red")
                return
        try:
            client = LoginMT5()
            # Actualiza credenciales desde el modal
            try:
                client.account = int(creds.get("cuenta", "0") or 0)
            except ValueError:
                client.account = 0
            client.password = creds.get("password", "")
            client.server = creds.get("servidor", "")

            self._log_info(f"Intentando conexión a MT5 con cuenta {client.account} en {client.server}…")
            connected = client.login()
            if connected:
                self._set_status("Conectado", "green")
                self._log_success("Conexión establecida correctamente.")
                # Try to populate symbol list from MT5
                self._populate_symbols()
                # Enable Start MT5 button and symbol/timeframe selectors
                try:
                    self.start_btn.state(["!disabled"])  
                except Exception:
                    self.start_btn.configure(state="normal")
                try:
                    self.symbol_cb.state(["!disabled"])  
                except Exception:
                    self.symbol_cb.configure(state="normal")
                try:
                    self.timeframe_cb.state(["!disabled"])  
                except Exception:
                    self.timeframe_cb.configure(state="normal")
                # If chart already started, refresh it
                try:
                    if self.chart_started and hasattr(self, "graphic") and hasattr(self.graphic, "refresh"):
                        self.graphic.refresh()
                except Exception:
                    pass
            else:
                self._set_status("Desconectado", "red")
                self._log_error("No se pudo establecer conexión (login() devolvió False).")
        except Exception as e:
            messagebox.showerror("Error de conexión", f"No se pudo conectar a MT5: {e}")
            self._set_status("Desconectado", "red")
            self._log_error(f"Excepción durante la conexión: {e}")

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
        self._save_prefs(symbol=symbol, timeframe=timeframe)
        # Only update the chart if it has been started
        if self.chart_started and symbol and hasattr(self, "graphic") and hasattr(self.graphic, "load_symbol"):
            self._log_info(f"Cambiando gráfico a {symbol} ({timeframe})")
            try:
                self.graphic.load_symbol(symbol=symbol, timeframe=timeframe)
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
        global DetectAllCandlesModal
        if DetectAllCandlesModal is None:
            try:
                from modals.detect_all_candles_modal import DetectAllCandlesModal as DACM
                DetectAllCandlesModal = DACM
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo abrir el modal de detección de velas: {e}")
                return
        
        modal = DetectAllCandlesModal(self.root)
        self.root.wait_window(modal)

        if hasattr(modal, 'result') and modal.result:
            self._log_info(f"Iniciando detección para los siguientes patrones: {', '.join(modal.result)}")
            self._run_pattern_analysis(modal.result)
        else:
            self._log_info("Detección de patrones cancelada.")

    def _open_detect_forex_modal(self):
        """Abre el modal para seleccionar y analizar estrategias de Forex."""
        global DetectAllForexModal
        if DetectAllForexModal is None:
            try:
                from modals.detect_all_forex_modal import DetectAllForexModal as DAFM
                DetectAllForexModal = DAFM
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo abrir el modal de estrategias: {e}")
                return
        
        modal = DetectAllForexModal(self.root)
        self.root.wait_window(modal)

        if hasattr(modal, 'result') and modal.result:
            self._log_info(f"Iniciando análisis para las siguientes estrategias: {', '.join(modal.result)}")
            self._run_strategy_analysis(modal.result)
        else:
            self._log_info("Análisis de estrategias cancelado.")

    def _apply_strategies_action(self):
        """Abre el modal para configurar y aplicar estrategias."""
        # Primero, verificar si el gráfico tiene datos válidos
        if not self.chart_started or not hasattr(self.graphic, 'candles_df') or self.graphic.candles_df is None or self.graphic.candles_df.empty:
            messagebox.showerror("Error de Simulación", "No hay datos de gráfico cargados. Por favor, inicie el gráfico con 'Iniciar MT5' antes de configurar una simulación.")
            return

        global StrategySimulatorModal
        if StrategySimulatorModal is None:
            try:
                from modals.strategy_simulator_modal import StrategySimulatorModal as SSM
                StrategySimulatorModal = SSM
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo abrir el simulador de estrategias: {e}")
                return
        
        # Pasar el DataFrame de velas y el logger al modal
        modal = StrategySimulatorModal(self.root, candles_df=self.graphic.candles_df, logger=self.logger)
        self.root.wait_window(modal)

        if hasattr(modal, 'result') and modal.result:
            self._log_info(f"Configuración de simulación guardada y simulación ejecutada.")
            # La lógica de ejecución ya está dentro del modal y el simulador
        else:
            self._log_info("Simulación de estrategias cancelada.")

    def _run_pattern_analysis(self, selected_patterns):
        """Ejecuta el análisis de patrones y muestra los resultados."""
        if not self.chart_started or not hasattr(self.graphic, 'candles_df') or self.graphic.candles_df is None:
            self._log_error("El gráfico no está iniciado o no hay datos de velas disponibles.")
            return
        
        if CandleDetector is None:
            self._log_error("El detector de velas no está disponible.")
            return

        try:
            # Crear una copia del DataFrame para el análisis para no afectar al original
            candles_df_copy = self.graphic.candles_df.copy()
            # Asegurar que las columnas estén en minúsculas para el detector
            candles_df_copy.columns = [col.lower() for col in candles_df_copy.columns]
            detector = CandleDetector(candles_df_copy)
            stats = detector.analyze_patterns(selected_patterns)

            # Formatear los resultados usando el método de la clase
            summary_lines, total_profit, total_loss = CandleDetector.format_analysis_summary(stats)
            self._display_analysis_summary(summary_lines, total_profit, total_loss)

        except Exception as e:
            self._log_error(f"Ocurrió un error durante el análisis de patrones: {e}")

    def _run_strategy_analysis(self, selected_strategies):
        """Ejecuta el análisis de estrategias y muestra los resultados."""
        if not self.chart_started or not hasattr(self.graphic, 'candles_df') or self.graphic.candles_df is None:
            self._log_error("El gráfico no está iniciado o no hay datos de velas disponibles.")
            return
        
        if StrategyAnalyzer is None:
            self._log_error("El analizador de estrategias no está disponible.")
            return

        try:
            # Crear una copia para no modificar el DataFrame original
            candles_df_copy = self.graphic.candles_df.copy()
            candles_df_copy.columns = [col.lower() for col in candles_df_copy.columns]
            
            # Aquí se podrían añadir indicadores necesarios para las estrategias
            # Ejemplo: df['ema_fast'] = df['close'].ewm(span=12, adjust=False).mean()

            analyzer = StrategyAnalyzer(candles_df_copy)
            stats = analyzer.analyze_strategies(selected_strategies)

            self._display_strategy_summary(stats)

        except Exception as e:
            self._log_error(f"Ocurrió un error durante el análisis de estrategias: {e}")

    def _display_analysis_summary(self, lines, total_profit, total_loss):
        """Muestra el resumen del análisis de patrones en el logger."""
        for line in lines:
            # El primer título y los totales tienen colores, el resto es info normal
            if "RESUMEN" in line or "="*15 in line:
                self._log_success(line)
            else:
                self._log_info(line)
        
        self.logger.log_summary(
            f"GANANCIA TOTAL (TODOS LOS PATRONES): {total_profit:.2f} $",
            f"PÉRDIDA TOTAL (TODOS LOS PATRONES): {total_loss:.2f} $"
        )
        self._log_success("="*75 + "\n")

    def _display_strategy_summary(self, stats):
        """Formatea y muestra el resumen del análisis de estrategias en el logger."""
        if StrategyAnalyzer is None:
            return

        summary_lines, total_profit, total_loss = StrategyAnalyzer.format_strategy_summary(stats)

        for line in summary_lines:
            if "RESUMEN" in line or "="*15 in line:
                self._log_success(line)
            else:
                self._log_info(line)

        self.logger.log_summary(
            f"BENEFICIO TOTAL (TODAS LAS ESTRATEGIAS): {total_profit:.2f} $",
            f"PÉRDIDA TOTAL (TODAS LAS ESTRATEGIAS): {total_loss:.2f} $"
        )
        self._log_success("="*75 + "\n")

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

            backtester = PerfectBacktester(candles_df_copy)
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

            for line in summary_lines:
                if "RESUMEN" in line or "="*25 in line:
                    self._log_success(line)
                else:
                    self._log_info(line)
            
            self._log_success(f"BENEFICIO TOTAL PERFECTO: {total_profit:.2f} $")
            self._log_success("="*90 + "\n")

        except Exception as e:
            self._log_error(f"Ocurrió un error durante el backtesting: {e}")

    def _finalize_backtesting_action(self):
        """Limpia los dibujos del gráfico y el contenido del logger."""
        if hasattr(self, 'graphic') and hasattr(self.graphic, 'clear_drawings'):
            self.graphic.clear_drawings()
            self._log_info("Dibujos del gráfico eliminados.")
        self._clear_log_action()

    def _iniciar_simulacion_action(self):
        """Lanza la simulación."""
        self._log_info("TODO: Iniciar simulación")

    def _abrir_operacion_manual_action(self):
        """Abre una operación manual."""
        self._log_info("TODO: Abriendo operación manual")

    def _modificar_estrategias_action(self):
        """Modifica las estrategias."""
        self._log_info("TODO: Modificar estrategias")

    def _cancelar_simulacion_action(self):
        """Cancela la simulación."""
        self._log_info("TODO: Cancelar simulación")

    def _clear_log_action(self):
        """Limpia el contenido del logger."""
        if hasattr(self, 'logger') and hasattr(self.logger, 'clear'):
            self.logger.clear()

    def _on_exit(self):
        try:
            # Save preferences on exit
            self._save_prefs(symbol=self.symbol_var.get(), timeframe=self.timeframe_var.get())
            # Close the Tkinter window gracefully
            self.root.destroy()
        finally:
            # Ensure all subprocesses/threads are terminated
            print("Saliendo del programa...")
            os._exit(0)


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()