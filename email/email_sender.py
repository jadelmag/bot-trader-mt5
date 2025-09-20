import os
import json
import smtplib
import ssl
import time
import threading
from email.message import EmailMessage

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "strategies", "config.json")

class EmailSender:
    """Gestiona el envío de notificaciones por correo electrónico en segundo plano."""

    def __init__(self, logger=None):
        self.logger = logger
        self.config = {}
        self.is_running = False
        self.thread = None
        self.reload_config()

    def _log(self, message, level="info"):
        if self.logger:
            if level == "error":
                self.logger.error(message)
            else:
                self.logger.log(message)

    def reload_config(self):
        """Carga o recarga la configuración desde el archivo JSON."""
        try:
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
            else:
                self.config = {}
        except (json.JSONDecodeError, IOError) as e:
            self._log(f"Error al cargar la configuración de email: {e}", "error")
            self.config = {}

    def start(self):
        """Inicia el hilo de envío de correos si está habilitado."""
        if self.is_running:
            return

        self.reload_config() # Asegurarse de tener la última config
        if not self.config.get("email_notifications") or not mt5:
            return

        self.is_running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        self._log("Servicio de notificaciones por email iniciado.")

    def stop(self):
        """Detiene el hilo de envío de correos."""
        if not self.is_running:
            return
        
        self.is_running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5) # Esperar a que el hilo termine
        self._log("Servicio de notificaciones por email detenido.")

    def _run(self):
        """Bucle principal que se ejecuta en el hilo."""
        interval_hours = self.config.get("email_interval_hours", 24)
        interval_seconds = interval_hours * 3600

        while self.is_running:
            try:
                self._send_status_email()
                # Esperar el intervalo, pero verificando periódicamente si debe detenerse
                for _ in range(int(interval_seconds)):
                    if not self.is_running:
                        return
                    time.sleep(1)
            except Exception as e:
                self._log(f"Error en el ciclo de envío de email: {e}", "error")
                # Esperar un tiempo antes de reintentar para no saturar
                time.sleep(60)

    def _get_account_summary(self):
        """Obtiene un resumen detallado del estado de la cuenta de MT5."""
        if not mt5 or not mt5.terminal_info():
            return "No hay conexión con MetaTrader 5."

        try:
            account_info = mt5.account_info()
            if not account_info:
                return "No se pudo obtener la información de la cuenta."

            # --- Datos Principales ---
            currency = account_info.currency
            balance = account_info.balance
            equity = account_info.equity
            profit_floating = account_info.profit
            leverage = account_info.leverage

            # --- Datos Históricos y Métricas ---
            history_deals = mt5.history_deals_get(0, int(time.time()))
            
            total_trades = 0
            wins = 0
            losses = 0
            gross_profit = 0
            gross_loss = 0
            most_profitable_trade = 0
            most_losing_trade = 0
            
            if history_deals:
                # Filtrar solo transacciones de entrada/salida
                trade_deals = [d for d in history_deals if d.entry in (mt5.DEAL_ENTRY_IN, mt5.DEAL_ENTRY_OUT)]
                total_trades = len(trade_deals)

                for deal in trade_deals:
                    if deal.profit > 0:
                        wins += 1
                        gross_profit += deal.profit
                        if deal.profit > most_profitable_trade:
                            most_profitable_trade = deal.profit
                    elif deal.profit < 0:
                        losses += 1
                        gross_loss += abs(deal.profit)
                        if deal.profit < most_losing_trade:
                            most_losing_trade = deal.profit

            win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
            avg_profit = (gross_profit / wins) if wins > 0 else 0
            avg_loss = (gross_loss / losses) if losses > 0 else 0
            profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')

            # --- Operaciones Abiertas ---
            positions = mt5.positions_get()
            open_positions_count = len(positions) if positions else 0

            # --- Construcción del Resumen ---
            summary = f"""
===============================
|         RESUMEN GENERAL         |
===============================

📌 Datos principales:
- Dinero inicial: No disponible
- Balance actual: {balance:.2f} {currency}
- Dinero total (incluyendo flotante): {equity:.2f} {currency}
- Ganancias acumuladas: No disponible
- Pérdidas acumuladas: No disponible
- Equity: {equity:.2f} {currency}
- Drawdown máximo: No disponible
- Apalancamiento usado: 1:{leverage}

📊 Operaciones:
- Número de operaciones realizadas: {total_trades}
- Número de operaciones forex abiertas: {open_positions_count} (Total)
- Número de operaciones candle abiertas: No disponible
- Operación más rentable: {most_profitable_trade:.2f} {currency}
- Operación más perdedora: {most_losing_trade:.2f} {currency}

📈 Métricas de rendimiento:
- Win Rate (%): {win_rate:.2f}%
- Promedio de ganancia por operación: {avg_profit:.2f} {currency}
- Promedio de pérdida por operación: {avg_loss:.2f} {currency}
- Relación Ganancia/Pérdida (Profit Factor): {profit_factor:.2f}
- Expectancy (ganancia esperada por operación): No disponible
- Tiempo promedio en operación: No disponible

===============================
            """
            return summary.strip()

        except Exception as e:
            return f"Error al obtener el resumen de la cuenta: {e}"

    def _send_status_email(self):
        """Construye y envía el correo electrónico de estado."""
        sender_email = self.config.get("email_address")
        password = self.config.get("email_password")

        if not sender_email or not password:
            self._log("Dirección de email o contraseña no configuradas.", "error")
            return

        # --- Asumimos Gmail, pero se podría hacer más genérico --- #
        smtp_server = "smtp.gmail.com"
        port = 465  # SSL

        subject = f"[Bot Trader MT5] Resumen de Cuenta - {time.strftime('%Y-%m-%d %H:%M')}"
        body = self._get_account_summary()

        msg = EmailMessage()
        msg.set_content(body)
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = sender_email # Enviarse a sí mismo

        try:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
                server.login(sender_email, password)
                server.send_message(msg)
                self._log(f"Email de estado enviado correctamente a {sender_email}.")
        except smtplib.SMTPAuthenticationError:
            self._log("Error de autenticación. Revisa el email y la contraseña. Si usas Gmail, puede que necesites una 'Contraseña de Aplicación'.", "error")
            self.stop() # Detener para no reintentar con credenciales incorrectas
        except Exception as e:
            self._log(f"No se pudo enviar el email: {e}", "error")
