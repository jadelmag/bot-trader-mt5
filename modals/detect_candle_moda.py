from candles.candle_list import CandlePatterns
# Importar el modal de configuración, manejando el caso de que aún no exista
try:
    from modals.candle_config_modal import CandleConfigModal
except ImportError:
    CandleConfigModal = None

import tkinter as tk
from tkinter import ttk
import os
import sys
import json

# Añadir el directorio raíz del proyecto a sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(CURRENT_DIR, '..')))

class DetectCandleModal(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Detectar Patrones de Velas")
        self.geometry("800x600")
        self.transient(parent)
        self.grab_set()

        self.patterns = self._get_candle_patterns()
        self.pattern_vars = {}
        self.pattern_widgets = {}

        self._build_ui()
        self._center_window()

    def _center_window(self):
        """Centra la ventana modal sobre su ventana padre."""
        self.update_idletasks()
        parent = self.master
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

    def _on_mousewheel(self, event):
        """Gestiona el scroll con la rueda del ratón."""
        if self.canvas.yview() == (0.0, 1.0) and event.delta > 0:
            return # No hacer scroll hacia arriba si ya está en el tope
        if self.canvas.yview()[1] >= 1.0 and event.delta < 0:
            return # No hacer scroll hacia abajo si ya está en el final
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _get_candle_patterns(self):
        """Obtiene la lista de nombres de patrones de velas desde la clase CandlePatterns."""
        all_pattern_functions = [
            func for func in dir(CandlePatterns) 
            if callable(getattr(CandlePatterns, func)) and func.startswith('is_')
        ]
        # Limpiar nombres: quitar 'is_' y reemplazar '_' con espacio
        pattern_names = [name.replace('is_', '').replace('_', ' ') for name in all_pattern_functions]
        return sorted(pattern_names)

    def _build_ui(self):
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(expand=True, fill=tk.BOTH)

        # --- Frame Superior para botones de acción ---
        top_button_frame = ttk.Frame(main_frame)
        top_button_frame.pack(fill=tk.X, pady=(0, 10))
        top_button_frame.columnconfigure(0, weight=1) # Para alinear a la derecha

        btn_select_all = ttk.Button(top_button_frame, text="Seleccionar Todos", command=self._select_all)
        btn_select_all.grid(row=0, column=1, padx=5)

        btn_deselect_all = ttk.Button(top_button_frame, text="Deseleccionar Todos", command=self._deselect_all)
        btn_deselect_all.grid(row=0, column=2, padx=5)

        btn_load_all = ttk.Button(top_button_frame, text="Cargar Todas las Estrategias", command=self._load_all_strategies)
        btn_load_all.grid(row=0, column=3, padx=5)

        # --- Canvas y Scrollbar para la lista de patrones ---
        canvas_frame = ttk.Frame(main_frame, borderwidth=1, relief="sunken")
        canvas_frame.pack(expand=True, fill=tk.BOTH)

        self.canvas = tk.Canvas(canvas_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        scrollable_frame = ttk.Frame(self.canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        # --- Bindings para el scroll del ratón ---
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        scrollable_frame.bind("<MouseWheel>", self._on_mousewheel)
        # Bind a todos los widgets hijos para que el scroll funcione en toda la lista
        self.bind_all("<MouseWheel>", self._on_mousewheel, add='+')
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # --- Llenar la lista de patrones ---
        self._populate_patterns(scrollable_frame)

        # --- Frame Inferior para botones Guardar/Cancelar ---
        bottom_button_frame = ttk.Frame(main_frame)
        bottom_button_frame.pack(fill=tk.X, pady=(10, 0))

        # Configurar columnas para centrar los botones
        bottom_button_frame.columnconfigure(0, weight=1)
        bottom_button_frame.columnconfigure(3, weight=1)

        btn_cancel = ttk.Button(bottom_button_frame, text="Cancelar", command=self._on_close)
        btn_cancel.grid(row=0, column=1, padx=5)

        btn_apply = ttk.Button(bottom_button_frame, text="Aplicar", command=self._apply_config)
        btn_apply.grid(row=0, column=2, padx=5)

    def _on_close(self):
        """Asegura que el binding del mousewheel se elimine al cerrar."""
        self.unbind_all("<MouseWheel>")
        self.destroy()

    def _populate_patterns(self, parent_frame):
        """Crea y añade las filas para cada patrón de vela."""
        for pattern_name in self.patterns:
            var = tk.BooleanVar()
            self.pattern_vars[pattern_name] = var

            row_frame = ttk.Frame(parent_frame, padding=(5, 5))
            row_frame.pack(fill=tk.X, expand=True)

            # Checkbox y Label
            chk = ttk.Checkbutton(row_frame, variable=var)
            chk.pack(side=tk.LEFT, padx=(0, 5))

            label_text = pattern_name.title().replace(' Is', '')
            lbl = ttk.Label(row_frame, text=label_text, width=25)
            lbl.pack(side=tk.LEFT, padx=5)

            # Dropdown para configuración
            config_type = ttk.Combobox(row_frame, values=["default", "custom"], width=10)
            config_type.set("default")
            config_type.pack(side=tk.LEFT, padx=5)

            # Botones de acción
            btn_config = ttk.Button(row_frame, text="Configurar Estrategia", command=lambda p=pattern_name: self._open_config_modal(p))
            btn_config.pack(side=tk.LEFT, padx=5)

            btn_load = ttk.Button(row_frame, text="Cargar Estrategia", command=lambda p=pattern_name: self._load_strategy(p))
            btn_load.pack(side=tk.LEFT, padx=5)

            # Guardar widgets para referencia futura
            self.pattern_widgets[pattern_name] = {'var': var, 'config_type': config_type}

    def _select_all(self):
        for var in self.pattern_vars.values():
            var.set(True)

    def _deselect_all(self):
        for var in self.pattern_vars.values():
            var.set(False)

    def _load_all_strategies(self):
        print("Cargando todas las estrategias...")
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        strategies_dir = os.path.join(project_root, 'strategies')

        if not os.path.isdir(strategies_dir):
            print("El directorio 'strategies' no existe.")
            return

        for filename in os.listdir(strategies_dir):
            if filename.endswith('.json'):
                pattern_name_from_file = filename.replace('.json', '').replace('_', ' ')
                # Normalizar el nombre para que coincida con las claves del diccionario
                for p_name in self.patterns:
                    if p_name.lower() == pattern_name_from_file.lower():
                        self._load_strategy(p_name, silent=True)
                        break
        print("Carga de todas las estrategias completada.")

    def _open_config_modal(self, pattern_name):
        if CandleConfigModal:
            modal = CandleConfigModal(self, pattern_name)
            self.wait_window(modal)
        else:
            print(f"Error: El modal de configuración no está disponible.")

    def _load_strategy(self, pattern_name, silent=False):
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        strategies_dir = os.path.join(project_root, 'strategies')
        config_file = os.path.join(strategies_dir, f"{pattern_name.lower().replace(' ', '_')}.json")

        if os.path.exists(config_file):
            if pattern_name in self.pattern_widgets:
                self.pattern_widgets[pattern_name]['var'].set(True)
                self.pattern_widgets[pattern_name]['config_type'].set('custom')
                if not silent:
                    print(f"Estrategia cargada para: {pattern_name}")
            else:
                if not silent:
                    print(f"Error: No se encontraron widgets para el patrón {pattern_name}")
        else:
            if not silent:
                print(f"No se encontró archivo de configuración para: {pattern_name}")

    def _apply_config(self):
        """Recopila la configuración seleccionada y la guarda en self.result antes de cerrar."""
        print("Aplicando configuración...")
        self.result = {}
        for name, widgets in self.pattern_widgets.items():
            # Solo incluir patrones que han sido marcados con el checkbox
            if widgets['var'].get():
                config_type = widgets['config_type'].get()
                self.result[name] = {'config_type': config_type}
        
        print("Configuración a aplicar:", self.result)
        self._on_close() # Usar _on_close para un cierre limpio