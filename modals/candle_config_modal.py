import tkinter as tk
from tkinter import ttk
import json
import os

class CandleConfigModal(tk.Toplevel):
    """Modal para configurar los parámetros de una estrategia de patrón de vela."""

    def __init__(self, parent, pattern_name):
        super().__init__(parent)
        self.parent = parent
        self.pattern_name = pattern_name
        self.display_name = pattern_name.replace('is_', '').replace('_', ' ').title()
        self.config_file_path = self._get_config_path()

        self.title(f"Configurar Estrategia: {self.display_name}")
        self.geometry("450x400")
        self.transient(parent)
        self.grab_set()

        self.config_vars = {}
        self.result = None

        self._build_ui()
        self._load_config()
        self._center_window()

        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def _get_config_path(self):
        """Obtiene la ruta al archivo de configuración para este patrón."""
        strategies_dir = os.path.join(os.path.dirname(__file__), '..', 'strategies')
        return os.path.join(strategies_dir, f"{self.pattern_name.replace('is_', '')}.json")

    def _build_ui(self):
        """Construye la interfaz de usuario del modal."""
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(expand=True, fill=tk.BOTH)

        # --- Notebook para las pestañas ---
        notebook = ttk.Notebook(main_frame)
        notebook.pack(expand=True, fill=tk.BOTH, pady=(0, 10))

        general_tab = ttk.Frame(notebook, padding=15)
        atr_tab = ttk.Frame(notebook, padding=15)

        notebook.add(general_tab, text="General")
        notebook.add(atr_tab, text="Parámetros ATR")

        self._populate_general_tab(general_tab)
        self._populate_atr_tab(atr_tab)

        # --- Botones inferiores ---
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        button_frame.columnconfigure(0, weight=1) # Centrar botones
        button_frame.columnconfigure(3, weight=1)

        btn_cancel = ttk.Button(button_frame, text="Cancelar", command=self._on_cancel)
        btn_cancel.grid(row=0, column=1, padx=5)

        btn_save = ttk.Button(button_frame, text="Guardar", command=self._save_config)
        btn_save.grid(row=0, column=2, padx=5)

    def _populate_general_tab(self, tab):
        """Llena la pestaña 'General' con los checkboxes."""
        options = {
            "use_signal_change": "Usar Cambio de Señal",
            "use_stop_loss": "Usar Stop Loss",
            "use_take_profit": "Usar Take Profit",
            "use_trailing_stop": "Usar Trailing Stop",
            "use_pattern_reversal": "Usar Reversión de Patrón"
        }
        for key, text in options.items():
            self.config_vars[key] = tk.BooleanVar()
            chk = ttk.Checkbutton(tab, text=text, variable=self.config_vars[key])
            chk.pack(anchor='w', pady=5, padx=5)

    def _populate_atr_tab(self, tab):
        """Llena la pestaña 'Parámetros ATR' con los campos de entrada numérica."""
        options = {
            "atr_sl_multiplier": "Multiplicador ATR para Stop Loss:",
            "atr_tp_multiplier": "Multiplicador ATR para Take Profit:",
            "atr_trailing_multiplier": "Multiplicador ATR para Trailing Stop:"
        }
        for key, text in options.items():
            row = ttk.Frame(tab)
            row.pack(fill='x', pady=5, padx=5)
            ttk.Label(row, text=text).pack(side='left')
            self.config_vars[key] = tk.DoubleVar()
            entry = ttk.Entry(row, textvariable=self.config_vars[key], width=10)
            entry.pack(side='right')

    def _load_config(self):
        """Carga la configuración existente desde el archivo JSON, si existe."""
        default_config = {
            "use_signal_change": True, "use_stop_loss": True, "use_take_profit": True,
            "use_trailing_stop": False, "use_pattern_reversal": False,
            "atr_sl_multiplier": 1.5, "atr_tp_multiplier": 3.0, "atr_trailing_multiplier": 1.5
        }

        config = default_config
        if os.path.exists(self.config_file_path):
            try:
                with open(self.config_file_path, 'r') as f:
                    loaded_config = json.load(f)
                # Asegurarse de que el archivo cargado no está corrupto y tiene todas las claves
                config.update(loaded_config)
            except (json.JSONDecodeError, TypeError):
                pass # Si hay error, se usan los valores por defecto

        for key, value in config.items():
            if key in self.config_vars:
                self.config_vars[key].set(value)

    def _save_config(self):
        """Guarda la configuración actual en el archivo JSON."""
        config_to_save = {key: var.get() for key, var in self.config_vars.items()}
        try:
            with open(self.config_file_path, 'w') as f:
                json.dump(config_to_save, f, indent=4)
            self.result = True # Indicar que se guardó
        except Exception as e:
            print(f"Error al guardar la configuración: {e}")
            self.result = False
        self.destroy()

    def _on_cancel(self):
        """Cierra el modal sin guardar."""
        self.result = False
        self.destroy()

    def _center_window(self):
        """Centra el modal en la ventana principal."""
        self.update_idletasks()
        x = self.parent.winfo_x() + (self.parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = self.parent.winfo_y() + (self.parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")