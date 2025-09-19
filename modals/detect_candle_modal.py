import tkinter as tk
from tkinter import ttk
import os
import sys
import inspect
import json

# --- Configuración de sys.path ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from candles.candle_list import CandlePatterns
from modals.candle_config_modal import CandleConfigModal

class DetectCandleModal(tk.Toplevel):
    """Modal para seleccionar y configurar estrategias para patrones de velas."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Aplicar Estrategias a Patrones de Velas")
        self.geometry("500x600")
        self.transient(parent)
        self.grab_set()

        self.patterns = self._get_candle_patterns()
        self.pattern_widgets = {}
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

    def _build_ui(self):
        """Construye la interfaz de usuario del modal."""
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(expand=True, fill=tk.BOTH)

        # --- Frame Superior para botones de selección ---
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))
        top_frame.columnconfigure(0, weight=1) # Empuja los botones a la derecha

        btn_select_all = ttk.Button(top_frame, text="Seleccionar Todos", command=self._select_all)
        btn_select_all.grid(row=0, column=1, padx=5)

        btn_deselect_all = ttk.Button(top_frame, text="Deseleccionar Todos", command=self._deselect_all)
        btn_deselect_all.grid(row=0, column=2, padx=5)

        btn_load_all = ttk.Button(top_frame, text="Cargar Todas las Estrategias", command=self._load_all_strategies)
        btn_load_all.grid(row=0, column=3, padx=5)

        # --- Contenedor para la lista con scroll ---
        list_container = ttk.Frame(main_frame, borderwidth=1, relief="sunken")
        list_container.pack(fill="both", expand=True, pady=5)

        canvas = tk.Canvas(list_container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Llenar la lista de patrones
        for i, pattern_name in enumerate(self.patterns):
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
            btn_load = ttk.Button(row_frame, text="Cargar", command=lambda p=pattern_name: self._load_strategy(p))
            btn_load.pack(side=tk.LEFT, padx=5)

            # Guardar referencias a los widgets de la fila
            self.pattern_widgets[pattern_name] = {
                'checkbox_var': var,
                'strategy_var': strategy_type_var,
                'load_button': btn_load
            }
            
            # Comprobar estado inicial del botón Cargar
            self._update_load_button_state(pattern_name)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Vincular scroll del ratón de forma global para este modal
        self.bind_all("<MouseWheel>", lambda event: self._on_mousewheel(event, canvas))

        # --- Frame Inferior para botones de acción ---
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X, pady=(10, 0))
        bottom_frame.columnconfigure(0, weight=1) # Centra los botones
        bottom_frame.columnconfigure(3, weight=1)

        btn_cancel = ttk.Button(bottom_frame, text="Cancelar", command=self._on_close)
        btn_cancel.grid(row=0, column=1, padx=5)

        btn_save = ttk.Button(bottom_frame, text="Iniciar", command=self._save_and_close)
        btn_save.grid(row=0, column=2, padx=5)

    def _center_window(self):
        """Centra el modal en la ventana principal."""
        self.update_idletasks()
        parent = self.master
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

    def _on_mousewheel(self, event, canvas):
        """Permite hacer scroll en la lista con la rueda del ratón."""
        # Solo hacer scroll si el canvas todavía existe
        if canvas.winfo_exists():
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_close(self):
        """Cierra el modal y, muy importante, desvincula el evento de scroll."""
        try:
            # Usar winfo_toplevel() para obtener la ventana raíz de forma segura
            self.winfo_toplevel().unbind_all("<MouseWheel>")
        except tk.TclError:
            # La ventana ya podría estar destruida, así que ignoramos el error
            pass
        self.destroy()

    # --- Funciones de los botones (placeholders) ---

    def _select_all(self):
        for widgets in self.pattern_widgets.values():
            widgets['checkbox_var'].set(True)

    def _deselect_all(self):
        for widgets in self.pattern_widgets.values():
            widgets['checkbox_var'].set(False)

    def _load_all_strategies(self):
        print("Acción: Cargar todas las estrategias")
        for pattern_name in self.patterns:
            self._load_strategy(pattern_name, update_ui=True)

    def _open_config_modal(self, pattern_name):
        """Abre el modal de configuración para un patrón específico."""
        config_modal = CandleConfigModal(self, pattern_name)
        self.wait_window(config_modal)

        # Si se guardó la configuración, actualizar el estado del botón Cargar
        if config_modal.result is True:
            self._update_load_button_state(pattern_name)

    def _load_strategy(self, pattern_name, update_ui=False):
        config_path = os.path.join(self.strategies_dir, f"{pattern_name.replace('is_', '')}.json")
        if os.path.exists(config_path):
            print(f"Cargando estrategia para: {pattern_name} desde {config_path}")
            # Aquí iría la lógica para leer y procesar el JSON
            
            # Cambiar dropdown a Custom
            if pattern_name in self.pattern_widgets:
                self.pattern_widgets[pattern_name]['strategy_var'].set("Custom")
        elif update_ui:
            # No hacer nada si se llama desde 'Cargar Todas' y el archivo no existe
            pass
        else:
            print(f"No se encontró archivo de configuración para: {pattern_name}")

    def _save_and_close(self):
        """Recopila la configuración actual y la guarda en strategies/strategies.json."""
        config_to_save = {}
        for pattern_name, widgets in self.pattern_widgets.items():
            config_to_save[pattern_name] = {
                'selected': widgets['checkbox_var'].get(),
                'strategy_mode': widgets['strategy_var'].get()
            }

        output_path = os.path.join(self.strategies_dir, 'strategies.json')
        try:
            with open(output_path, 'w') as f:
                json.dump(config_to_save, f, indent=4)
            print(f"Configuración guardada correctamente en {output_path}")
        except Exception as e:
            print(f"Error al guardar la configuración: {e}")
            # Opcional: mostrar un messagebox.showerror aquí

        self.result = config_to_save # Devolvemos la configuración para uso futuro
        self._on_close()

    def _update_load_button_state(self, pattern_name):
        """Comprueba si existe el JSON de la estrategia y actualiza el estado del botón."""
        config_path = os.path.join(self.strategies_dir, f"{pattern_name.replace('is_', '')}.json")
        button = self.pattern_widgets[pattern_name]['load_button']
        if os.path.exists(config_path):
            button.config(state=tk.NORMAL)
        else:
            button.config(state=tk.DISABLED)
