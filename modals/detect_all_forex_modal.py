import tkinter as tk
from tkinter import ttk
import os
import sys
import inspect

# --- Configuración de sys.path ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

class DetectAllForexModal(tk.Toplevel):
    """Modal para seleccionar y ejecutar análisis de estrategias de Forex."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Detectar Estrategias Forex")
        self.geometry("450x500")
        self.transient(parent)
        self.grab_set()

        self.strategies = self._get_forex_strategies()
        self.strategy_vars = {}
        self.result = None

        self._build_ui()
        self._center_window()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _get_forex_strategies(self):
        """Obtiene una lista de nombres de estrategias desde la clase ForexStrategies."""
        # Lazy import para evitar problemas en el arranque
        from forex.forex_list import ForexStrategies
        strategy_methods = inspect.getmembers(ForexStrategies, predicate=inspect.isfunction)
        # Filtra solo los métodos que comienzan con 'strategy_'
        strategy_names = [name for name, func in strategy_methods if name.startswith('strategy_')]
        return sorted(strategy_names)

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

        # --- Contenedor para la lista con scroll ---
        list_container = ttk.Frame(main_frame, borderwidth=1, relief="sunken")
        list_container.pack(fill="both", expand=True, pady=5)

        self.canvas = tk.Canvas(list_container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=self.canvas.yview)
        scrollable_frame = ttk.Frame(self.canvas)

        scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        # Llenar la lista de estrategias
        for strategy_name in self.strategies:
            var = tk.BooleanVar()
            self.strategy_vars[strategy_name] = var
            # Formatear el nombre para mostrarlo más limpio
            display_name = strategy_name.replace('strategy_', '').replace('_', ' ').title()
            chk = ttk.Checkbutton(scrollable_frame, text=display_name, variable=var)
            chk.pack(anchor='w', padx=10, pady=3)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Vincular scroll del ratón
        self.bind_all("<MouseWheel>", self._on_mousewheel, add='+')

        # --- Frame Inferior para botones de acción ---
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X, pady=(10, 0))
        bottom_frame.columnconfigure(0, weight=1) # Centra los botones
        bottom_frame.columnconfigure(3, weight=1)

        btn_cancel = ttk.Button(bottom_frame, text="Cancelar", command=self._on_close)
        btn_cancel.grid(row=0, column=1, padx=5)

        btn_start = ttk.Button(bottom_frame, text="Iniciar", command=self._start_analysis)
        btn_start.grid(row=0, column=2, padx=5)

    def _center_window(self):
        """Centra el modal en la ventana principal."""
        self.update_idletasks()
        parent = self.master
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

    def _on_mousewheel(self, event):
        """Permite hacer scroll en la lista con la rueda del ratón."""
        if self.canvas.winfo_exists():
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _select_all(self):
        """Selecciona todos los checkboxes."""
        for var in self.strategy_vars.values():
            var.set(True)

    def _deselect_all(self):
        """Deselecciona todos los checkboxes."""
        for var in self.strategy_vars.values():
            var.set(False)

    def _start_analysis(self):
        """Guarda las estrategias seleccionadas y cierra el modal."""
        self.result = [name for name, var in self.strategy_vars.items() if var.get()]
        if not self.result:
            self.result = None
        self._on_close()

    def _on_close(self):
        """Cierra el modal y desvincula el evento de scroll."""
        try:
            root = self.winfo_toplevel()
            root.unbind_all("<MouseWheel>")
        except tk.TclError:
            pass # La ventana ya podría estar destruida
        self.destroy()