import tkinter as tk
from tkinter import ttk
import os
from dotenv import load_dotenv

# Carga las variables de entorno para que estén disponibles
load_dotenv()

class LoginModal(tk.Toplevel):
    def __init__(self, parent: tk.Tk):
        super().__init__(parent)
        self.title("Conectar a MT5")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.columnconfigure(0, weight=1)

        container = ttk.Frame(self, padding=16)
        container.grid(row=0, column=0, sticky="nsew")
        for i in range(2):
            container.columnconfigure(i, weight=1)

        # Labels and entries
        ttk.Label(container, text="Cuenta:").grid(row=0, column=0, sticky="e", padx=(0, 8), pady=(0, 8))
        self.cuenta_var = tk.StringVar(value=os.getenv("MT5_ACCOUNT", ""))
        cuenta_entry = ttk.Entry(container, textvariable=self.cuenta_var, width=30)
        cuenta_entry.grid(row=0, column=1, sticky="w", pady=(0, 8))

        ttk.Label(container, text="Password:").grid(row=1, column=0, sticky="e", padx=(0, 8), pady=(0, 8))
        self.password_var = tk.StringVar(value=os.getenv("MT5_PASSWORD", ""))
        password_entry = ttk.Entry(container, textvariable=self.password_var, width=30, show="*")
        password_entry.grid(row=1, column=1, sticky="w", pady=(0, 8))

        ttk.Label(container, text="Servidor:").grid(row=2, column=0, sticky="e", padx=(0, 8), pady=(0, 8))
        self.servidor_var = tk.StringVar(value=os.getenv("MT5_SERVER", ""))
        servidor_entry = ttk.Entry(container, textvariable=self.servidor_var, width=30)
        servidor_entry.grid(row=2, column=1, sticky="w", pady=(0, 8))

        # Buttons
        buttons = ttk.Frame(container)
        buttons.grid(row=3, column=0, columnspan=2, sticky="e", pady=(8, 0))

        cancelar_btn = ttk.Button(buttons, text="Cancelar", command=self._on_cancel)
        cancelar_btn.grid(row=0, column=0, padx=(0, 8))

        conectar_btn = ttk.Button(buttons, text="Conectar", command=self._on_submit)
        conectar_btn.grid(row=0, column=1)

        # Center over parent
        self.update_idletasks()
        self._center_over_parent(parent)

        # Focus
        cuenta_entry.focus_set()

        # Bindings
        self.bind("<Return>", lambda e: self._on_submit())
        self.bind("<Escape>", lambda e: self._on_cancel())

        # Ensure window close uses cancel
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def _center_over_parent(self, parent: tk.Tk):
        self.update_idletasks()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()

        w = self.winfo_width()
        h = self.winfo_height()
        x = px + (pw // 2) - (w // 2)
        y = py + (ph // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _on_submit(self):
        # Here you could trigger connection logic or emit an event
        self.result = {
            "cuenta": self.cuenta_var.get(),
            "password": self.password_var.get(),
            "servidor": self.servidor_var.get(),
        }
        self.grab_release()
        self.destroy()

    def _on_cancel(self):
        self.result = None
        self.grab_release()
        self.destroy()