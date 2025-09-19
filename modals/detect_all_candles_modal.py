import tkinter as tk
from tkinter import ttk
import os
import sys

# Añadir el directorio raíz del proyecto a sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from candles.candle_list import CandlePatterns

class DetectAllCandlesModal(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Detectar Patrones de Velas en Gráfico")
        self.geometry("400x400")
        self.transient(parent)
        self.grab_set()

        self.patterns = self._get_candle_patterns()
        self.pattern_vars = {}
        self.result = None

        self._build_ui()
        self._center_window()
        # Forzar el cálculo del scrollregion después de que la ventana se haya dibujado
        self.after(100, lambda: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

    def _on_mousewheel(self, event):
        """Permite hacer scroll en la lista con la rueda del ratón."""
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _center_window(self):
        self.update_idletasks()
        parent = self.master
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

    def _get_candle_patterns(self):
        all_pattern_functions = [
            func for func in dir(CandlePatterns) 
            if callable(getattr(CandlePatterns, func)) and func.startswith('is_')
        ]
        pattern_names = [name.replace('is_', '') for name in all_pattern_functions]
        return sorted(pattern_names)

    def _build_ui(self):
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(expand=True, fill=tk.BOTH)

        # --- Frame Superior ---
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))
        top_frame.columnconfigure(0, weight=1)

        btn_select_all = ttk.Button(top_frame, text="Seleccionar Todos", command=self._select_all)
        btn_select_all.grid(row=0, column=1, padx=5)

        btn_deselect_all = ttk.Button(top_frame, text="Deseleccionar Todos", command=self._deselect_all)
        btn_deselect_all.grid(row=0, column=2, padx=5)

        # --- Contenedor para la lista y el scroll ---
        list_container = ttk.Frame(main_frame, borderwidth=1, relief="sunken")
        list_container.pack(fill="both", expand=True, pady=5)

        self.canvas = tk.Canvas(list_container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=self.canvas.yview)
        scrollable_frame = ttk.Frame(self.canvas)

        self.canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        # Llenar la lista
        for pattern_name in self.patterns:
            var = tk.BooleanVar()
            self.pattern_vars[pattern_name] = var
            chk = ttk.Checkbutton(scrollable_frame, text=pattern_name.replace('_', ' ').title(), variable=var)
            chk.pack(anchor='w', padx=10, pady=2)

        # Colocar los elementos en el contenedor
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Vincular el scroll del ratón
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel, add='+')
        self.protocol("WM_DELETE_WINDOW", lambda: self.canvas.unbind_all("<MouseWheel>"))

        # --- Frame Inferior ---
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X, pady=(10, 0))
        bottom_frame.columnconfigure(0, weight=1)
        bottom_frame.columnconfigure(3, weight=1)

        btn_cancel = ttk.Button(bottom_frame, text="Cancelar", command=self.destroy)
        btn_cancel.grid(row=0, column=1, padx=5)

        btn_start = ttk.Button(bottom_frame, text="Iniciar", command=self._start_detection)
        btn_start.grid(row=0, column=2, padx=5)

    def _select_all(self):
        for var in self.pattern_vars.values():
            var.set(True)

    def _deselect_all(self):
        for var in self.pattern_vars.values():
            var.set(False)

    def _start_detection(self):
        self.result = [name for name, var in self.pattern_vars.items() if var.get()]
        if not self.result:
            self.result = None
        self._on_close()

    def _on_close(self):
        # Desvincular el evento de scroll para no afectar a otras ventanas
        # Es crucial llamar a unbind_all en la ventana raíz (root)
        # para eliminar un binding creado con bind_all.
        try:
            root = self.winfo_toplevel()
            root.unbind_all("<MouseWheel>")
        except tk.TclError:
            # La ventana ya podría estar destruida, ignorar el error.
            pass
        self.destroy()