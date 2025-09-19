import tkinter as tk
from tkinter import ttk
import json
import os

class CandleConfigModal(tk.Toplevel):
    def __init__(self, parent, pattern_name):
        super().__init__(parent)
        self.pattern_name = pattern_name
        self.config_path = self._get_config_path()

        self.title(f"Configurar Estrategia: {pattern_name.title()}")
        self.geometry("450x350")
        self.transient(parent)
        self.grab_set()

        self.config_vars = {}
        self._load_initial_config()
        self._build_ui()
        self._center_window()

    def _center_window(self):
        """Centra la ventana modal sobre su ventana padre."""
        self.update_idletasks()
        parent = self.master
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

    def _get_config_path(self):
        """Genera la ruta al archivo de configuración para este patrón."""
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        strategies_dir = os.path.join(project_root, 'strategies')
        filename = f"{self.pattern_name.lower().replace(' ', '_')}.json"
        return os.path.join(strategies_dir, filename)

    def _load_initial_config(self):
        """Carga la configuración desde el archivo JSON si existe, si no, usa los valores por defecto."""
        default_config = {
            "use_signal_change": True,
            "use_stop_loss": True,
            "use_take_profit": True,
            "use_trailing_stop": False,
            "use_pattern_reversal": False,
            "atr_sl_multiplier": 1.5,
            "atr_tp_multiplier": 3.0,
            "atr_trailing_multiplier": 1.5
        }

        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    loaded_config = json.load(f)
                # Asegurarse de que todas las claves por defecto están presentes
                for key, value in default_config.items():
                    if key not in loaded_config:
                        loaded_config[key] = value
                config = loaded_config
            except (json.JSONDecodeError, TypeError):
                config = default_config
        else:
            config = default_config

        # Crear variables de Tkinter
        for key, value in config.items():
            if isinstance(value, bool):
                self.config_vars[key] = tk.BooleanVar(value=value)
            else:
                self.config_vars[key] = tk.DoubleVar(value=value)

    def _build_ui(self):
        main_frame = ttk.Frame(self, padding=15)
        main_frame.pack(expand=True, fill=tk.BOTH)

        # --- Controles de configuración (sin pestañas por ahora) ---
        controls_frame = ttk.Frame(main_frame, padding=10, borderwidth=1, relief="groove")
        controls_frame.pack(expand=True, fill=tk.BOTH, pady=(0, 15))

        # Añadir todos los controles directamente para depuración
        self._populate_general_tab(controls_frame)
        ttk.Separator(controls_frame, orient='horizontal').pack(fill='x', pady=10, padx=5)
        self._populate_atr_tab(controls_frame)

        # Botones inferiores
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)

        btn_save = ttk.Button(button_frame, text="Guardar", command=self._save_config)
        btn_save.grid(row=0, column=0, sticky="e", padx=5)

        btn_cancel = ttk.Button(button_frame, text="Cancelar", command=self.destroy)
        btn_cancel.grid(row=0, column=1, sticky="w", padx=5)

    def _populate_general_tab(self, parent_frame):
        boolean_options = [
            ("use_signal_change", "Usar Cambio de Señal"),
            ("use_stop_loss", "Usar Stop Loss"),
            ("use_take_profit", "Usar Take Profit"),
            ("use_trailing_stop", "Usar Trailing Stop"),
            ("use_pattern_reversal", "Usar Reversión de Patrón")
        ]
        for key, text in boolean_options:
            chk = ttk.Checkbutton(parent_frame, text=text, variable=self.config_vars[key])
            chk.pack(anchor="w", pady=4, padx=5)

    def _populate_atr_tab(self, parent_frame):
        float_options = [
            ("atr_sl_multiplier", "Multiplicador ATR para Stop Loss:"),
            ("atr_tp_multiplier", "Multiplicador ATR para Take Profit:"),
            ("atr_trailing_multiplier", "Multiplicador ATR para Trailing Stop:")
        ]
        
        # Usar un frame y grid para alinear labels y spinboxes
        atr_grid_frame = ttk.Frame(parent_frame)
        atr_grid_frame.pack(fill='x', padx=5)

        for i, (key, text) in enumerate(float_options):
            ttk.Label(atr_grid_frame, text=text).grid(row=i, column=0, sticky="w", pady=5)
            spinbox = tk.Spinbox(
                atr_grid_frame, 
                from_=0.0, 
                to=100.0, 
                increment=0.1, 
                textvariable=self.config_vars[key], 
                width=8,
                wrap=False
            )
            spinbox.grid(row=i, column=1, sticky="e", padx=10)
        
        atr_grid_frame.columnconfigure(1, weight=1)

    def _save_config(self):
        """Recopila los valores de la UI y los guarda en el archivo JSON."""
        config_data = {key: var.get() for key, var in self.config_vars.items()}

        # Asegurarse de que el directorio 'strategies' existe
        strategies_dir = os.path.dirname(self.config_path)
        os.makedirs(strategies_dir, exist_ok=True)

        try:
            with open(self.config_path, 'w') as f:
                json.dump(config_data, f, indent=4)
            print(f"Configuración guardada en: {self.config_path}")
        except IOError as e:
            print(f"Error al guardar el archivo de configuración: {e}")
        
        self.destroy()