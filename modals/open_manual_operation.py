import os
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None


class OpenManualOperationModal(tk.Toplevel):
    """Modal para abrir operaciones manuales en MT5."""

    def __init__(self, parent, symbol, logger=None):
        super().__init__(parent)
        self.transient(parent)
        self.title("Abrir Operación Manual")
        self.resizable(False, False)
        self.result = None
        self.symbol = symbol
        self.logger = logger

        # Variables para los campos
        self._init_variables()

        # Construir UI
        self._build_ui()
        self._center_window(600, 350)

        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.grab_set()

    def _init_variables(self):
        """Inicializa todas las variables del formulario."""
        # Tab 1: Atributos básicos
        self.symbol_var = tk.StringVar(value=self.symbol)
        self.volume_var = tk.StringVar(value="0.01")
        self.order_type_var = tk.StringVar(value="buy")
        self.price_var = tk.StringVar(value=self._get_current_price())
        self.deviation_var = tk.StringVar(value="20")
        self.comment_var = tk.StringVar(value="operacion manual")

        # Tab 2: Gestión de riesgo
        self.sl_var = tk.StringVar(value="")
        self.tp_var = tk.StringVar(value="")
        self.risk_percent_var = tk.StringVar(value="1.0")
        self.use_trailing_stop_var = tk.BooleanVar(value=True)
        self.trailing_distance_var = tk.StringVar(value="50")

        # Tab 3: Atributos adicionales
        self.magic_number_var = tk.StringVar(value="123456")
        self.expiration_var = tk.StringVar(value="")
        self.slippage_var = tk.StringVar(value="2")
        self.partial_close_percent_var = tk.StringVar(value="50")
        self.trailing_step_var = tk.StringVar(value="10")

        # Variables para mensajes de error
        self.volume_error_var = tk.StringVar(value="")

    def _get_current_price(self):
        """Obtiene el precio actual del símbolo."""
        if not mt5 or not mt5.terminal_info():
            return "0.00000"
        
        try:
            tick = mt5.symbol_info_tick(self.symbol)
            if tick:
                return f"{(tick.bid + tick.ask) / 2:.5f}"
        except Exception:
            pass
        return "0.00000"

    def _center_window(self, w: int, h: int):
        """Centra la ventana modal respecto al padre."""
        self.update_idletasks()
        parent_x = self.master.winfo_x()
        parent_y = self.master.winfo_y()
        parent_w = self.master.winfo_width()
        parent_h = self.master.winfo_height()

        x = parent_x + (parent_w // 2) - (w // 2)
        y = parent_y + (parent_h // 2) - (h // 2)

        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self):
        """Construye la interfaz con tabs."""
        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(expand=True, fill="both")

        # Crear notebook (tabs)
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(expand=True, fill="both", pady=(0, 15))

        # Tab 1: Atributos básicos
        tab1 = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(tab1, text="Atributos Básicos")
        self._build_basic_tab(tab1)

        # Tab 2: Gestión de riesgo
        tab2 = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(tab2, text="Gestión de Riesgo")
        self._build_risk_tab(tab2)

        # Tab 3: Atributos adicionales
        tab3 = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(tab3, text="Atributos Adicionales")
        self._build_additional_tab(tab3)

        # Botones
        self._build_buttons(main_frame)

    def _build_basic_tab(self, parent):
        """Construye el tab de atributos básicos."""
        row = 0

        # Moneda
        ttk.Label(parent, text="Moneda:").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        symbol_combo = ttk.Combobox(parent, textvariable=self.symbol_var, state="readonly", width=25)
        symbol_combo["values"] = (self.symbol,)
        symbol_combo.grid(row=row, column=1, sticky="ew", pady=5, padx=5)
        row += 1

        # Volumen
        ttk.Label(parent, text="Volumen:").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        volume_entry = ttk.Entry(parent, textvariable=self.volume_var, width=27)
        volume_entry.grid(row=row, column=1, sticky="ew", pady=5, padx=5)
        volume_entry.bind("<KeyRelease>", self._validate_volume)
        row += 1

        # Mensaje de error de volumen
        error_label = ttk.Label(parent, textvariable=self.volume_error_var, foreground="red", font=("", 8))
        error_label.grid(row=row, column=1, sticky="w", padx=5)
        row += 1

        # Orden
        ttk.Label(parent, text="Orden:").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        order_combo = ttk.Combobox(parent, textvariable=self.order_type_var, state="readonly", width=25)
        order_combo["values"] = ("buy", "sell", "buy_limit", "sell_limit", "buy_stop", "sell_stop")
        order_combo.grid(row=row, column=1, sticky="ew", pady=5, padx=5)
        order_combo.bind("<<ComboboxSelected>>", self._on_order_type_change)
        row += 1

        # Precio
        ttk.Label(parent, text="Precio:").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        ttk.Entry(parent, textvariable=self.price_var, width=27).grid(row=row, column=1, sticky="ew", pady=5, padx=5)
        row += 1

        # Desviación
        ttk.Label(parent, text="Desviación:").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        ttk.Entry(parent, textvariable=self.deviation_var, width=27).grid(row=row, column=1, sticky="ew", pady=5, padx=5)
        row += 1

        # Comentario
        ttk.Label(parent, text="Comentario:").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        comment_entry = ttk.Entry(parent, textvariable=self.comment_var, width=27)
        comment_entry.grid(row=row, column=1, sticky="ew", pady=5, padx=5)
        comment_entry.bind("<KeyRelease>", lambda e: self._limit_comment())
        row += 1

        parent.columnconfigure(1, weight=1)

    def _build_risk_tab(self, parent):
        """Construye el tab de gestión de riesgo."""
        row = 0

        # SL (Stop Loss)
        ttk.Label(parent, text="SL (Stop Loss):").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        sl_frame = ttk.Frame(parent)
        sl_frame.grid(row=row, column=1, sticky="ew", pady=5, padx=5)
        ttk.Entry(sl_frame, textvariable=self.sl_var, width=15).pack(side="left")
        ttk.Button(sl_frame, text="Sugerir", command=lambda: self._suggest_sl(), width=10).pack(side="left", padx=5)
        row += 1

        # TP (Take Profit)
        ttk.Label(parent, text="TP (Take Profit):").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        tp_frame = ttk.Frame(parent)
        tp_frame.grid(row=row, column=1, sticky="ew", pady=5, padx=5)
        ttk.Entry(tp_frame, textvariable=self.tp_var, width=15).pack(side="left")
        ttk.Button(tp_frame, text="Sugerir", command=lambda: self._suggest_tp(), width=10).pack(side="left", padx=5)
        row += 1

        # Risk Percent
        ttk.Label(parent, text="Riesgo (% del balance):").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        ttk.Entry(parent, textvariable=self.risk_percent_var, width=27).grid(row=row, column=1, sticky="ew", pady=5, padx=5)
        row += 1

        # Use Trailing Stop
        ttk.Checkbutton(parent, text="Activar Trailing Stop", variable=self.use_trailing_stop_var).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=5, padx=5
        )
        row += 1

        # Trailing Distance
        ttk.Label(parent, text="Distancia Trailing (puntos):").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        ttk.Entry(parent, textvariable=self.trailing_distance_var, width=27).grid(row=row, column=1, sticky="ew", pady=5, padx=5)
        row += 1

        parent.columnconfigure(1, weight=1)

    def _build_additional_tab(self, parent):
        """Construye el tab de atributos adicionales."""
        row = 0

        # Magic Number
        ttk.Label(parent, text="Magic Number:").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        ttk.Entry(parent, textvariable=self.magic_number_var, width=27).grid(row=row, column=1, sticky="ew", pady=5, padx=5)
        row += 1

        # Expiration
        ttk.Label(parent, text="Expiración (YYYY-MM-DD HH:MM:SS):").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        ttk.Entry(parent, textvariable=self.expiration_var, width=27).grid(row=row, column=1, sticky="ew", pady=5, padx=5)
        row += 1

        # Slippage
        ttk.Label(parent, text="Deslizamiento (pips):").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        ttk.Entry(parent, textvariable=self.slippage_var, width=27).grid(row=row, column=1, sticky="ew", pady=5, padx=5)
        row += 1

        # Partial Close Percent
        ttk.Label(parent, text="Cierre Parcial (%):").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        ttk.Entry(parent, textvariable=self.partial_close_percent_var, width=27).grid(row=row, column=1, sticky="ew", pady=5, padx=5)
        row += 1

        # Trailing Step
        ttk.Label(parent, text="Paso Trailing:").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        ttk.Entry(parent, textvariable=self.trailing_step_var, width=27).grid(row=row, column=1, sticky="ew", pady=5, padx=5)
        row += 1

        parent.columnconfigure(1, weight=1)

    def _build_buttons(self, parent):
        """Construye los botones de acción."""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill="x", pady=(10, 0))

        ttk.Button(button_frame, text="Crear", command=self._on_create).pack(side="right", padx=(10, 0))
        ttk.Button(button_frame, text="Cancelar", command=self._on_cancel).pack(side="right")

    def _validate_volume(self, event=None):
        """Valida que el volumen sea compatible con MT5."""
        volume_str = self.volume_var.get()
        
        if not volume_str:
            self.volume_error_var.set("")
            return True

        try:
            volume = float(volume_str)
            
            if not mt5 or not mt5.terminal_info():
                self.volume_error_var.set("No hay conexión con MT5")
                return False

            symbol_info = mt5.symbol_info(self.symbol)
            if not symbol_info:
                self.volume_error_var.set("No se pudo obtener información del símbolo")
                return False

            # Validar volumen mínimo
            if volume < symbol_info.volume_min:
                self.volume_error_var.set(f"Volumen mínimo: {symbol_info.volume_min}")
                return False

            # Validar volumen máximo
            if volume > symbol_info.volume_max:
                self.volume_error_var.set(f"Volumen máximo: {symbol_info.volume_max}")
                return False

            # Validar step de volumen
            volume_step = symbol_info.volume_step
            if volume_step > 0:
                steps = round(volume / volume_step)
                if abs(volume - steps * volume_step) > 1e-10:
                    self.volume_error_var.set(f"El volumen debe ser múltiplo de {volume_step}")
                    return False

            self.volume_error_var.set("")
            return True

        except ValueError:
            self.volume_error_var.set("Debe ser un número válido")
            return False

    def _limit_comment(self):
        """Limita el comentario a 25 caracteres."""
        comment = self.comment_var.get()
        if len(comment) > 25:
            self.comment_var.set(comment[:25])

    def _on_order_type_change(self, event=None):
        """Actualiza el precio sugerido cuando cambia el tipo de orden."""
        order_type = self.order_type_var.get()
        
        # Para órdenes de mercado, actualizar el precio actual
        if order_type in ("buy", "sell"):
            self.price_var.set(self._get_current_price())

    def _suggest_sl(self):
        """Sugiere un precio de Stop Loss basado en el precio actual."""
        try:
            price = float(self.price_var.get())
            order_type = self.order_type_var.get()
            
            if not mt5 or not mt5.terminal_info():
                return
            
            symbol_info = mt5.symbol_info(self.symbol)
            if not symbol_info:
                return
            
            point = symbol_info.point
            digits = symbol_info.digits
            
            # Sugerir SL a 50 pips de distancia
            sl_pips = 50
            
            if order_type in ("buy", "buy_limit", "buy_stop"):
                sl = round(price - sl_pips * point * 10, digits)
            else:
                sl = round(price + sl_pips * point * 10, digits)
            
            self.sl_var.set(f"{sl:.{digits}f}")
            
        except ValueError:
            pass

    def _suggest_tp(self):
        """Sugiere un precio de Take Profit basado en el precio actual."""
        try:
            price = float(self.price_var.get())
            order_type = self.order_type_var.get()
            
            if not mt5 or not mt5.terminal_info():
                return
            
            symbol_info = mt5.symbol_info(self.symbol)
            if not symbol_info:
                return
            
            point = symbol_info.point
            digits = symbol_info.digits
            
            # Sugerir TP a 100 pips de distancia
            tp_pips = 100
            
            if order_type in ("buy", "buy_limit", "buy_stop"):
                tp = round(price + tp_pips * point * 10, digits)
            else:
                tp = round(price - tp_pips * point * 10, digits)
            
            self.tp_var.set(f"{tp:.{digits}f}")
            
        except ValueError:
            pass

    def _on_create(self):
        """Crea la operación manual."""
        # Validar volumen
        if not self._validate_volume():
            messagebox.showerror("Error de Validación", "El volumen no es válido.", parent=self)
            return

        try:
            # Construir el diccionario de operación manual
            manual_trade = {
                "symbol": self.symbol_var.get(),
                "order_type": self.order_type_var.get(),
                "volume": float(self.volume_var.get()),
                "price": float(self.price_var.get()) if self.price_var.get() else None,
                "sl": float(self.sl_var.get()) if self.sl_var.get() else None,
                "tp": float(self.tp_var.get()) if self.tp_var.get() else None,
                "deviation": int(self.deviation_var.get()) if self.deviation_var.get() else 20,
                "comment": self.comment_var.get(),
                "magic_number": int(self.magic_number_var.get()) if self.magic_number_var.get() else 123456,
                "risk_percent": float(self.risk_percent_var.get()) if self.risk_percent_var.get() else None,
                "use_trailing_stop": self.use_trailing_stop_var.get(),
                "trailing_distance": int(self.trailing_distance_var.get()) if self.trailing_distance_var.get() else 50,
                "expiration": self.expiration_var.get() if self.expiration_var.get() else None,
                "slippage": float(self.slippage_var.get()) if self.slippage_var.get() else 2,
                "partial_close_percent": float(self.partial_close_percent_var.get()) if self.partial_close_percent_var.get() else 50,
                "trailing_step": int(self.trailing_step_var.get()) if self.trailing_step_var.get() else 10
            }

            self.result = manual_trade
            self.destroy()

        except ValueError as e:
            messagebox.showerror("Error de Validación", f"Por favor, verifica que todos los campos numéricos sean válidos:\n{e}", parent=self)

    def _on_cancel(self):
        """Cancela la creación de la operación."""
        self.result = None
        self.destroy()