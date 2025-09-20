import os
import json
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "strategies", "config.json")

class ConfigAppModal(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.transient(parent)
        self.title("Configuración de la Aplicación")
        self.resizable(False, False)
        self.result = None

        # --- Variables --- #
        self.email_notifications_var = tk.BooleanVar()
        self.email_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.interval_var = tk.StringVar()
        self.money_limit_var = tk.StringVar()
        self.audit_log_var = tk.BooleanVar()
        self.risk_per_trade_var = tk.StringVar(value="1.0") # Default 1%

        # --- Layout --- #
        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(expand=True, fill="both")

        self._build_email_section(main_frame)
        self._build_general_section(main_frame)
        self._build_buttons(main_frame)

        self._load_config()
        self._center_window(500, 400)

        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.grab_set() # Modal behavior

    def _center_window(self, w: int, h: int):
        """Centra la ventana modal con respecto a su padre."""
        self.update_idletasks()
        parent_x = self.master.winfo_x()
        parent_y = self.master.winfo_y()
        parent_w = self.master.winfo_width()
        parent_h = self.master.winfo_height()

        x = parent_x + (parent_w // 2) - (w // 2)
        y = parent_y + (parent_h // 2) - (h // 2)

        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build_email_section(self, parent):
        email_frame = ttk.LabelFrame(parent, text="Notificaciones por Email", padding="10")
        email_frame.pack(fill="x", pady=(0, 15))

        ttk.Checkbutton(
            email_frame, 
            text="Activar notificaciones por email",
            variable=self.email_notifications_var
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

        ttk.Label(email_frame, text="Correo Electrónico:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(email_frame, textvariable=self.email_var, width=40).grid(row=1, column=1, sticky="ew", padx=5)

        ttk.Label(email_frame, text="Contraseña:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(email_frame, textvariable=self.password_var, show="*", width=40).grid(row=2, column=1, sticky="ew", padx=5)

        ttk.Label(email_frame, text="Intervalo (horas):").grid(row=3, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(email_frame, textvariable=self.interval_var, width=10).grid(row=3, column=1, sticky="w", padx=5)

        email_frame.columnconfigure(1, weight=1)

    def _build_general_section(self, parent):
        general_frame = ttk.LabelFrame(parent, text="Configuración General", padding="10")
        general_frame.pack(fill="x", pady=(0, 15))

        # Money Limit
        limit_frame = ttk.Frame(general_frame)
        limit_frame.pack(fill="x", pady=5)
        ttk.Label(limit_frame, text="Capital Mínimo para Operar:").pack(side="left", padx=5)
        ttk.Entry(limit_frame, textvariable=self.money_limit_var, width=15).pack(side="left")

        # Risk per Trade
        risk_frame = ttk.Frame(general_frame)
        risk_frame.pack(fill="x", pady=5)
        ttk.Label(risk_frame, text="Riesgo por Operación (%):").pack(side="left", padx=5)
        ttk.Entry(risk_frame, textvariable=self.risk_per_trade_var, width=15).pack(side="left")

        # Audit Log
        audit_frame = ttk.Frame(general_frame)
        audit_frame.pack(fill="x", pady=5)
        ttk.Checkbutton(
            audit_frame, 
            text="Habilitar log de auditoría de operaciones (JSONL)",
            variable=self.audit_log_var
        ).pack(side="left", padx=5)

    def _build_buttons(self, parent):
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill="x", pady=(10, 0))

        ttk.Button(button_frame, text="Guardar", command=self._on_save).pack(side="right", padx=(10, 0))
        ttk.Button(button_frame, text="Cancelar", command=self._on_cancel).pack(side="right")

    def _load_config(self):
        if not os.path.exists(CONFIG_PATH):
            return
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)
            
            self.email_notifications_var.set(config.get("email_notifications", False))
            self.email_var.set(config.get("email_address", ""))
            self.password_var.set(config.get("email_password", ""))
            self.interval_var.set(str(config.get("email_interval_hours", "24")))
            self.money_limit_var.set(str(config.get("money_limit", "")))
            self.audit_log_var.set(config.get("audit_log_enabled", False))
            self.risk_per_trade_var.set(str(config.get("risk_per_trade_percent", "1.0")))

        except (json.JSONDecodeError, TypeError):
            messagebox.showerror("Error", f"El archivo de configuración '{os.path.basename(CONFIG_PATH)}' está corrupto.", parent=self)

    def _on_save(self):
        try:
            # Validation
            interval_hours = int(self.interval_var.get()) if self.interval_var.get() else 0
            money_limit = float(self.money_limit_var.get()) if self.money_limit_var.get() else 0.0
            risk_percent = float(self.risk_per_trade_var.get()) if self.risk_per_trade_var.get() else 1.0

            if self.email_notifications_var.get() and not self.email_var.get():
                messagebox.showwarning("Campo Requerido", "El correo electrónico es obligatorio si las notificaciones están activadas.", parent=self)
                return

            config = {
                "email_notifications": self.email_notifications_var.get(),
                "email_address": self.email_var.get(),
                "email_password": self.password_var.get(),
                "email_interval_hours": interval_hours,
                "money_limit": money_limit,
                "audit_log_enabled": self.audit_log_var.get(),
                "risk_per_trade_percent": risk_percent
            }

            # Ensure directory exists
            os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)

            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
            
            self.result = True
            self.destroy()

        except ValueError:
            messagebox.showerror("Error de Validación", "Por favor, introduce un número válido para el intervalo, límite y riesgo.", parent=self)
        except Exception as e:
            messagebox.showerror("Error al Guardar", f"No se pudo guardar la configuración: {e}", parent=self)

    def _on_cancel(self):
        self.result = False
        self.destroy()