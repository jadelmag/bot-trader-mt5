import tkinter as tk
from tkinter import ttk, messagebox
import os
import sys
import inspect
import json

# --- Configuración de sys.path ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from modals.candle_config_modal import CandleConfigModal
from forex.forex_list import ForexStrategies
from backtesting.strategy_simulator import StrategySimulator
from candles.candle_list import CandlePatterns

class SimulationStrategiesModal(tk.Toplevel):
    """Modal para seleccionar y configurar estrategias de Forex y Velas."""

    def __init__(self, parent, candles_df, logger):
        super().__init__(parent)
        self.title("Simulador de Estrategias")
        self.geometry("650x600")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        # --- Datos y Logger ---
        self.candles_df = candles_df
        self.logger = logger

        # --- Candle Patterns ---
        self.candle_patterns = self._get_candle_patterns()
        self.candle_widgets = {}
        
        # --- Forex Strategies ---
        self.forex_strategies = self._get_forex_strategies()
        self.forex_widgets = {}

        # --- Valores por defecto para estrategias Forex ---
        self.strategy_defaults = {
            "strategy_bollinger_bands_breakout": {"percent_ratio": 1.0, "rr_ratio": 1.5, "sl": 25.0},
            "strategy_candle_pattern_reversal": {"percent_ratio": 1.0, "rr_ratio": 2.5, "sl": 30.0},
            "strategy_chart_pattern_breakout": {"percent_ratio": 1.0, "rr_ratio": 2.0, "sl": 20.0},
            "strategy_ma_crossover": {"percent_ratio": 1.0, "rr_ratio": 2.0, "sl": 20.0},
            "strategy_ichimoku_kinko_hyo": {"percent_ratio": 1.0, "rr_ratio": 2.0, "sl": 30.0},
            "strategy_price_action_sr": {"percent_ratio": 1.0, "rr_ratio": 2.0, "sl": 20.0},
            "strategy_scalping_stochrsi_ema": {"percent_ratio": 0.5, "rr_ratio": 1.5, "sl": 30.0},
            "strategy_swing_trading_multi_indicator": {"percent_ratio": 1.5, "rr_ratio": 3.0, "sl": 30.0},
        }

        # --- UI Components ---
        self.notebook = None
        self.forex_canvas = None
        self.candle_canvas = None

        self.result = None

        # Asegurarse de que el directorio de estrategias existe
        self.strategies_dir = os.path.join(PROJECT_ROOT, 'strategies')
        os.makedirs(self.strategies_dir, exist_ok=True)

        self._build_ui()
        self._center_window()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _get_candle_patterns(self):
        """Obtiene una lista de todos los patrones de velas de la clase CandlePatterns."""
        pattern_methods = inspect.getmembers(CandlePatterns, predicate=inspect.isfunction)
        # Filtra solo los métodos que comienzan con 'is_'
        pattern_names = [name for name, func in pattern_methods if name.startswith('is_')]
        return sorted(pattern_names)

    def _get_forex_strategies(self):
        """Obtiene una lista de todas las estrategias de la clase ForexStrategies."""
        strategy_methods = inspect.getmembers(ForexStrategies, predicate=inspect.isfunction)
        # Filtra solo los métodos que comienzan con 'strategy_'
        strategy_names = [name for name, func in strategy_methods if name.startswith('strategy_')]
        return sorted(strategy_names)

    def _build_ui(self):
        """Construye la interfaz de usuario del modal con pestañas."""
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(expand=True, fill=tk.BOTH)

        # --- Notebook para las pestañas ---
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(expand=True, fill=tk.BOTH, pady=(0, 10))

        forex_tab = ttk.Frame(self.notebook, padding=10)
        candle_tab = ttk.Frame(self.notebook, padding=10)

        self.notebook.add(forex_tab, text="Forex")
        self.notebook.add(candle_tab, text="Candle")

        # Construir el contenido de cada pestaña
        self._build_forex_tab(forex_tab)
        self._build_candle_tab(candle_tab)

        # Vincular el evento de la rueda del ratón después de crear los canvas
        self.bind_all("<MouseWheel>", self._on_mousewheel)

        # --- Frame para los Slots y Capital Inicial ---
        config_frame = ttk.Frame(main_frame)
        config_frame.pack(fill=tk.X, pady=(10, 5))
        config_frame.columnconfigure((0, 4), weight=1) # Columnas para centrar

        # Fila para Slots
        ttk.Label(config_frame, text="Slots Forex:").grid(row=0, column=1, sticky='e', padx=(0, 5), pady=(5,0))
        self.slots_forex_var = tk.IntVar(value=1)
        forex_slots_entry = ttk.Entry(config_frame, textvariable=self.slots_forex_var, width=5)
        forex_slots_entry.grid(row=0, column=2, sticky='w', pady=(5,0))

        ttk.Label(config_frame, text="Slots Candles:").grid(row=0, column=3, sticky='e', padx=(10, 5), pady=(5,0))
        self.slots_candles_var = tk.IntVar(value=1)
        candle_slots_entry = ttk.Entry(config_frame, textvariable=self.slots_candles_var, width=5)
        candle_slots_entry.grid(row=0, column=4, sticky='w', pady=(5,0))

        # --- Frame Inferior para botones de acción (siempre visible) ---
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X, pady=(5, 0))
        bottom_frame.columnconfigure(0, weight=1) # Centra los botones
        bottom_frame.columnconfigure(3, weight=1)

        btn_cancel = ttk.Button(bottom_frame, text="Cancelar", command=self._on_close)
        btn_cancel.grid(row=0, column=1, padx=5)

        btn_apply = ttk.Button(bottom_frame, text="Aplicar", command=self._apply_and_run_simulation)
        btn_apply.grid(row=0, column=2, padx=5)

    def _build_forex_tab(self, tab):
        """Construye el contenido de la pestaña de estrategias Forex."""
        # --- Frame Superior para botones de selección ---
        top_frame = ttk.Frame(tab)
        top_frame.pack(fill=tk.X, pady=(0, 10))
        top_frame.columnconfigure(0, weight=1) # Empuja los botones a la derecha

        btn_select_all = ttk.Button(top_frame, text="Seleccionar Todos", command=self._select_all_forex)
        btn_select_all.grid(row=0, column=1, padx=5)

        btn_deselect_all = ttk.Button(top_frame, text="Deseleccionar Todos", command=self._deselect_all_forex)
        btn_deselect_all.grid(row=0, column=2, padx=5)

        # --- Contenedor para la lista con scroll ---
        list_container = ttk.Frame(tab, borderwidth=1, relief="sunken")
        list_container.pack(fill="both", expand=True, pady=5)

        self.forex_canvas = tk.Canvas(list_container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=self.forex_canvas.yview)
        scrollable_frame = ttk.Frame(self.forex_canvas)

        scrollable_frame.bind("<Configure>", lambda e: self.forex_canvas.configure(scrollregion=self.forex_canvas.bbox("all")))
        self.forex_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        self.forex_canvas.configure(yscrollcommand=scrollbar.set)

        # Llenar la lista de estrategias Forex
        for i, strategy_name in enumerate(self.forex_strategies):
            row_frame = ttk.Frame(scrollable_frame, padding=(5, 5))
            row_frame.pack(fill=tk.X, expand=True)

            var = tk.BooleanVar()
            
            # Checkbox
            chk = ttk.Checkbutton(row_frame, variable=var)
            chk.pack(side=tk.LEFT, padx=(5, 10))

            # Label con el nombre de la estrategia
            display_name = strategy_name.replace('strategy_', '').replace('_', ' ').title()
            lbl = ttk.Label(row_frame, text=display_name, width=25)
            lbl.pack(side=tk.LEFT, padx=5)

            # --- Entradas para % Ratio y RR Ratio ---
            # Stop Loss
            sl_var = tk.DoubleVar(value=self.strategy_defaults.get(strategy_name, {}).get('sl', 20.0))
            sl_entry = ttk.Entry(row_frame, textvariable=sl_var, width=8)
            sl_entry.pack(side=tk.RIGHT, padx=5)
            ttk.Label(row_frame, text="Stop Loss (pips):").pack(side=tk.RIGHT)

            # RR Ratio
            rr_ratio_var = tk.DoubleVar(value=self.strategy_defaults.get(strategy_name, {}).get('rr_ratio', 2.0))
            rr_entry = ttk.Entry(row_frame, textvariable=rr_ratio_var, width=8)
            rr_entry.pack(side=tk.RIGHT, padx=5)
            ttk.Label(row_frame, text="RR Ratio:").pack(side=tk.RIGHT)

            # % Ratio
            percent_ratio_var = tk.DoubleVar(value=self.strategy_defaults.get(strategy_name, {}).get('percent_ratio', 1.0))
            percent_entry = ttk.Entry(row_frame, textvariable=percent_ratio_var, width=8)
            percent_entry.pack(side=tk.RIGHT, padx=5)
            ttk.Label(row_frame, text="% Ratio:").pack(side=tk.RIGHT)

            self.forex_widgets[strategy_name] = {
                'checkbox_var': var,
                'percent_ratio_var': percent_ratio_var,
                'rr_ratio_var': rr_ratio_var,
                'sl_var': sl_var
            }

        self.forex_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _build_candle_tab(self, tab):
        """Construye el contenido de la pestaña de patrones de velas."""
        # --- Frame Superior para botones de selección ---
        top_frame = ttk.Frame(tab)
        top_frame.pack(fill=tk.X, pady=(0, 10))
        top_frame.columnconfigure(0, weight=1) # Empuja los botones a la derecha

        btn_select_all = ttk.Button(top_frame, text="Seleccionar Todos", command=self._select_all_candles)
        btn_select_all.grid(row=0, column=1, padx=5)

        btn_deselect_all = ttk.Button(top_frame, text="Deseleccionar Todos", command=self._deselect_all_candles)
        btn_deselect_all.grid(row=0, column=2, padx=5)

        btn_load_all = ttk.Button(top_frame, text="Cargar Todas las Estrategias", command=self._load_all_candle_strategies)
        btn_load_all.grid(row=0, column=3, padx=5)

        # --- Contenedor para la lista con scroll ---
        list_container = ttk.Frame(tab, borderwidth=1, relief="sunken")
        list_container.pack(fill="both", expand=True, pady=5)

        self.candle_canvas = tk.Canvas(list_container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=self.candle_canvas.yview)
        scrollable_frame = ttk.Frame(self.candle_canvas)

        scrollable_frame.bind("<Configure>", lambda e: self.candle_canvas.configure(scrollregion=self.candle_canvas.bbox("all")))
        self.candle_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        self.candle_canvas.configure(yscrollcommand=scrollbar.set)

        # Llenar la lista de patrones
        for i, pattern_name in enumerate(self.candle_patterns):
            row_frame = ttk.Frame(scrollable_frame, padding=(0, 5))
            row_frame.pack(fill=tk.X, expand=True)

            var = tk.BooleanVar()
            
            # Checkbox
            chk = ttk.Checkbutton(row_frame, variable=var)
            chk.pack(side=tk.LEFT, padx=(5, 10))

            # Label con el nombre del patrón
            display_name = pattern_name.replace('is_', '').replace('_', ' ').title()
            lbl = ttk.Label(row_frame, text=display_name, width=25)
            lbl.pack(side=tk.LEFT, padx=5)

            # Dropdown (Combobox)
            strategy_type_var = tk.StringVar(value="Default")
            dropdown = ttk.Combobox(row_frame, textvariable=strategy_type_var, values=["Default", "Custom"], width=10, state="readonly")
            dropdown.pack(side=tk.LEFT, padx=5)

            # Botón Configurar
            btn_config = ttk.Button(row_frame, text="Configurar", command=lambda p=pattern_name: self._open_config_modal(p))
            btn_config.pack(side=tk.LEFT, padx=5)

            # Botón Cargar
            btn_load = ttk.Button(row_frame, text="Cargar", command=lambda p=pattern_name: self._load_candle_strategy(p))
            btn_load.pack(side=tk.LEFT, padx=5)

            # Guardar referencias a los widgets de la fila
            self.candle_widgets[pattern_name] = {
                'checkbox_var': var,
                'strategy_var': strategy_type_var,
                'load_button': btn_load
            }
            
            # Comprobar estado inicial del botón Cargar
            self._update_load_button_state(pattern_name)

        self.candle_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _center_window(self):
        """Centra el modal en la ventana principal."""
        self.update_idletasks()
        parent = self.master
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

    def _on_mousewheel(self, event):
        """Maneja el scroll del ratón para la pestaña activa en el notebook."""
        if not self.notebook:
            return

        selected_tab_text = self.notebook.tab(self.notebook.select(), "text")

        canvas_to_scroll = None
        if selected_tab_text == "Forex" and self.forex_canvas and self.forex_canvas.winfo_exists():
            canvas_to_scroll = self.forex_canvas
        elif selected_tab_text == "Candle" and self.candle_canvas and self.candle_canvas.winfo_exists():
            canvas_to_scroll = self.candle_canvas

        if canvas_to_scroll:
            canvas_to_scroll.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_close(self):
        """Cierra el modal y, muy importante, desvincula el evento de scroll."""
        try:
            # Usar winfo_toplevel() para obtener la ventana raíz de forma segura
            self.winfo_toplevel().unbind_all("<MouseWheel>")
        except tk.TclError:
            # La ventana ya podría estar destruida, así que ignoramos el error
            pass
        self.destroy()

    # --- Funciones de los botones (CANDLE) ---

    def _select_all_candles(self):
        for widgets in self.candle_widgets.values():
            widgets['checkbox_var'].set(True)

    def _deselect_all_candles(self):
        for widgets in self.candle_widgets.values():
            widgets['checkbox_var'].set(False)

    def _load_all_candle_strategies(self):
        for pattern_name in self.candle_patterns:
            self._load_candle_strategy(pattern_name)

    def _open_config_modal(self, pattern_name):
        """Abre el modal de configuración para un patrón específico."""
        config_modal = CandleConfigModal(self, pattern_name)
        self.wait_window(config_modal)

        # Si se guardó la configuración, actualizar el estado del botón Cargar
        if config_modal.result is True:
            self._update_load_button_state(pattern_name)

    def _load_candle_strategy(self, pattern_name):
        """Carga una estrategia de velas desde un archivo JSON."""
        config_path = os.path.join(self.strategies_dir, f"{pattern_name.replace('is_', '')}.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    # Leemos el archivo para asegurarnos de que es un JSON válido
                    json.load(f)
                
                # Si la lectura es exitosa, cambiamos el dropdown a Custom
                if pattern_name in self.candle_widgets:
                    self.candle_widgets[pattern_name]['strategy_var'].set("Custom")

            except (json.JSONDecodeError, IOError) as e:
                messagebox.showerror("Error de Configuración", f"No se pudo cargar la estrategia para '{pattern_name}'.\nEl archivo podría estar corrupto.\n\nError: {e}")
    

    def _apply_and_run_simulation(self):
        """Recopila la config, la guarda, la devuelve y cierra el modal."""
        config_to_save = {
            'slots': {
                'forex': self.slots_forex_var.get(),
                'candle': self.slots_candles_var.get()
            },
            'candle_strategies': {},
            'forex_strategies': {}
        }

        # Recopilar datos de la pestaña Candle
        for pattern_name, widgets in self.candle_widgets.items():
            config_to_save['candle_strategies'][pattern_name] = {
                'selected': widgets['checkbox_var'].get(),
                'strategy_mode': widgets['strategy_var'].get()
            }
        
        # Recopilar datos de la pestaña Forex
        for strategy_name, widgets in self.forex_widgets.items():
            config_to_save['forex_strategies'][strategy_name] = {
                'selected': widgets['checkbox_var'].get(),
                'percent_ratio': widgets['percent_ratio_var'].get(),
                'rr_ratio': widgets['rr_ratio_var'].get(),
                'stop_loss_pips': widgets['sl_var'].get()
            }

        output_path = os.path.join(self.strategies_dir, 'strategies.json')
        try:
            with open(output_path, 'w') as f:
                json.dump(config_to_save, f, indent=4)
            self.logger.log("Configuración de estrategias guardada en 'strategies.json'.")
        except Exception as e:
            self.logger.error(f"Error al guardar la configuración: {e}")

        # Devolvemos la configuración para que la ventana principal la use
        self.result = config_to_save 
        self._on_close()

    def _update_load_button_state(self, pattern_name):
        """Comprueba si existe el JSON de la estrategia y actualiza el estado del botón."""
        config_path = os.path.join(self.strategies_dir, f"{pattern_name.replace('is_', '')}.json")
        button = self.candle_widgets[pattern_name]['load_button']
        if os.path.exists(config_path):
            button.config(state=tk.NORMAL)
        else:
            button.config(state=tk.DISABLED)

    def _select_all_forex(self):
        for widgets in self.forex_widgets.values():
            widgets['checkbox_var'].set(True)

    def _deselect_all_forex(self):
        for widgets in self.forex_widgets.values():
            widgets['checkbox_var'].set(False)