import tkinter as tk
from tkinter import messagebox

try:
    from modals.loggin_modal import LoginModal
    from loggin.loggin import LoginMT5
    import MetaTrader5 as mt5
except ImportError as e:
    print(f"Error al importar en LoginHandler: {e}")
    LoginModal = None
    LoginMT5 = None
    mt5 = None

class LoginHandler:
    def __init__(self, app):
        self.app = app

    def open_login_modal(self):
        """Abre el modal de login y gestiona el resultado."""
        if LoginModal is None:
            messagebox.showerror("Error", "El componente de login no está disponible.")
            return

        modal = LoginModal(self.app.root)
        self.app.root.wait_window(modal)
        result = getattr(modal, "result", None)

        if result:
            self._attempt_login(result)

    def _attempt_login(self, creds: dict):
        """Intenta conectar a MT5 con las credenciales proporcionadas."""
        if LoginMT5 is None:
            messagebox.showerror("Error", "El componente de conexión a MT5 no está disponible.")
            self.app._set_status("Error", "red")
            return

        try:
            client = LoginMT5(
                account=creds.get("cuenta"),
                password=creds.get("contraseña"),
                server=creds.get("servidor")
            )

            self.app._log_info(f"Intentando conexión a MT5 con cuenta {client.account} en {client.server}…")
            connected = client.login()

            if connected:
                self.app._set_status("Conectado", "green")
                self.app._log_success("Conexión establecida correctamente.")
                self._populate_symbols()
                self._enable_controls()
                
                if self.app.chart_started:
                    self.app.graphic.load_symbol(
                        symbol=self.app.symbol_var.get(),
                        timeframe=self.app.timeframe_var.get(),
                        queue=self.app.queue
                    )
            else:
                self.app._set_status("Error", "red")
                self.app._log_error("No se pudo establecer conexión (login() devolvió False).")
        except Exception as e:
            messagebox.showerror("Error de conexión", f"No se pudo conectar a MT5: {e}")
            self.app._set_status("Error", "red")
            self.app._log_error(f"Excepción durante la conexión: {e}")

    def _enable_controls(self):
        """Habilita los controles de la UI tras una conexión exitosa."""
        try:
            self.app.start_btn.state(["!disabled"])
            self.app.symbol_cb.state(["!disabled"])
            self.app.timeframe_cb.state(["!disabled"])
        except tk.TclError:
            self.app.start_btn.configure(state="normal")
            self.app.symbol_cb.configure(state="normal")
            self.app.timeframe_cb.configure(state="normal")

    def _populate_symbols(self):
        """Obtiene y popula la lista de símbolos de Forex desde MT5."""
        if mt5 is None or not mt5.terminal_info():
            return

        try:
            symbols = mt5.symbols_get()
            if not symbols:
                return

            forex_syms = [s.name for s in symbols if "forex" in s.path.lower() and s.visible]
            if not forex_syms:
                forex_syms = [s.name for s in symbols if "forex" in s.path.lower()]

            commons = [
                "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD",
                "EURJPY", "EURGBP", "EURCHF", "GBPJPY",
            ]
            ordered_unique = list(dict.fromkeys(commons + sorted(set(forex_syms))))
            self.app.symbol_cb.configure(values=ordered_unique)

            current = self.app.symbol_var.get()
            if current not in ordered_unique:
                self.app.symbol_var.set(ordered_unique[0] if ordered_unique else "")

        except Exception as e:
            self.app._log_error(f"Error al poblar símbolos: {e}")
