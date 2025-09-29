import os
import MetaTrader5 as mt5
import threading
from datetime import datetime
from tkinter import messagebox

try:
    from modals.detect_all_candles_modal import DetectAllCandlesModal
    from modals.detect_all_forex_modal import DetectAllForexModal
    from modals.strategy_simulator_modal import StrategySimulatorModal
    from modals.config_app_modal import ConfigAppModal
    from loggin.audit_log import AuditLogger
except ImportError as e:
    print(f"Error al importar modales en ActionHandler: {e}")
    DetectAllCandlesModal = None
    DetectAllForexModal = None
    StrategySimulatorModal = None
    ConfigAppModal = None
    AuditLogger = None

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class ActionHandler:
    def __init__(self, app):
        self.app = app
        self.create_required_dirs()

    def create_required_dirs(self):
        """Crea los directorios necesarios para la aplicación si no existen."""
        dirs_to_create = ["email", "audit", "simulation_logs"]
        for dir_name in dirs_to_create:
            try:
                os.makedirs(os.path.join(_project_root, dir_name), exist_ok=True)
            except OSError as e:
                self.app._log_error(f"No se pudo crear el directorio '{dir_name}': {e}")

    def save_chart_to_csv(self):
        """Guarda los datos del gráfico actual en un archivo CSV en la carpeta 'audit'."""
        if not self.app.chart_started or not hasattr(self.app, 'graphic') or self.app.graphic.candles_df is None or self.app.graphic.candles_df.empty:
            messagebox.showwarning("Sin Datos", "No hay datos de gráfico para guardar. Por favor, inicie el gráfico primero.")
            return
        
        try:
            df_to_save = self.app.graphic.candles_df.copy()
            
            df_to_save.reset_index(inplace=True)
            df_to_save.rename(columns={'time': 'Date', 'Open': 'Open', 'High': 'High', 'Low': 'Low', 'Close': 'Close', 'Volume': 'Volume'}, inplace=True)
            
            required_columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
            df_to_save = df_to_save[required_columns]
            
            symbol = self.app.symbol_var.get()
            timeframe = self.app.timeframe_var.get()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"chart_{symbol}_{timeframe}_{timestamp}.csv"
            
            save_path = os.path.join(_project_root, 'audit', filename)

            df_to_save.to_csv(save_path, index=False, date_format='%Y-%m-%d %H:%M:%S')
            
            self.app._log_success(f"Gráfico guardado correctamente en: {save_path}")
            messagebox.showinfo("Éxito", f"El gráfico se ha guardado como '{filename}' en la carpeta 'audit'.")

        except Exception as e:
            self.app._log_error(f"No se pudo guardar el gráfico en CSV: {e}")
            messagebox.showerror("Error al Guardar", f"Ocurrió un error al guardar el archivo: {e}")

    def clear_log(self):
        """Limpia el contenido del widget de logger."""
        if hasattr(self.app, 'logger') and hasattr(self.app.logger, 'clear_log'):
            self.app.logger.clear_log()

    def open_detect_candle_modal(self):
        """Abre el modal para detectar patrones de velas."""
        if DetectAllCandlesModal is None:
            messagebox.showerror("Error", "El componente de detección de velas no está disponible.")
            return
        
        modal = DetectAllCandlesModal(self.app.root)
        self.app.root.wait_window(modal)

        if hasattr(modal, 'result') and modal.result:
            self.app._log_info(f"Iniciando detección para los siguientes patrones: {', '.join(modal.result)}")
            self.app.analysis_handler.run_pattern_analysis(modal.result)
        else:
            self.app._log_info("Detección de patrones cancelada.")

    def open_detect_forex_modal(self):
        """Abre el modal para analizar estrategias de Forex."""
        if DetectAllForexModal is None:
            messagebox.showerror("Error", "El componente de estrategias de Forex no está disponible.")
            return
        
        modal = DetectAllForexModal(self.app.root)
        self.app.root.wait_window(modal)

        if hasattr(modal, 'result') and modal.result:
            self.app._log_info(f"Iniciando análisis para las siguientes estrategias: {', '.join(modal.result)}")
            self.app.analysis_handler.run_strategy_analysis(modal.result)
        else:
            self.app._log_info("Análisis de estrategias cancelado.")

    def apply_strategies_action(self):
        """Abre el modal para configurar y aplicar estrategias de simulación."""
        if not self.app.chart_started or not hasattr(self.app.graphic, 'candles_df') or self.app.graphic.candles_df.empty:
            messagebox.showerror("Error de Simulación", "No hay datos de gráfico cargados. Inicie el gráfico antes de configurar una simulación.")
            return

        if StrategySimulatorModal is None:
            messagebox.showerror("Error", "El simulador de estrategias no está disponible.")
            return
        
        modal = StrategySimulatorModal(self.app.root, candles_df=self.app.graphic.candles_df, logger=self.app.logger)
        self.app.root.wait_window(modal)

        if hasattr(modal, 'result') and modal.result:
            self.app._log_info("Configuración de simulación guardada y simulación ejecutada.")
        else:
            self.app._log_info("Simulación de estrategias cancelada.")

    def open_config_modal(self):
        """Abre el modal de configuración de la aplicación."""
        if ConfigAppModal is None:
            messagebox.showerror("Error", "El modal de configuración no está disponible.")
            return
        
        modal = ConfigAppModal(self.app.root)
        self.app.root.wait_window(modal)

        if hasattr(modal, 'result') and modal.result:
            self.app._log_info("Configuración guardada correctamente.")
            if AuditLogger:
                AuditLogger()._load_config()
                AuditLogger()._setup_log_file()
        else:
            self.app._log_info("La configuración no fue modificada.")

    def save_session_log(self):
        """Guarda el contenido actual del logger en un archivo de sesión."""
        if not hasattr(self.app.logger, 'get_content'):
            self.app._log_error("El logger no soporta la exportación de contenido.")
            return

        try:
            log_content = self.app.logger.get_content()
            if not log_content.strip():
                return  # No guardar si el log está vacío

            log_dir = os.path.join(_project_root, 'simulation_logs')
            # La creación de directorios ya se hace en __init__

            timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
            filename = f"simulacion_{timestamp}.log"
            
            save_path = os.path.join(log_dir, filename)

            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(log_content)
            
            self.app._log_success(f"Log de la sesión guardado en: {save_path}")

        except Exception as e:
            self.app._log_error(f"No se pudo guardar el log de la sesión: {e}")

    def _close_operations_in_thread(self, open_positions, pending_orders):
        """Cierra operaciones en hilo separado para evitar bloquear la UI."""
        def close_operations():
            try:
                success_count = 0
                total_count = len(open_positions or []) + len(pending_orders or [])
                
                # Cerrar posiciones
                if open_positions:
                    for pos in open_positions:
                        try:
                            from operations.manage_operations import close_single_operation
                            if close_single_operation(pos.ticket, 'position', self.app.logger):
                                success_count += 1
                        except Exception as e:
                            self.app._log_error(f"Error cerrando posición {pos.ticket}: {e}")
                
                # Cancelar órdenes
                if pending_orders:
                    for order in pending_orders:
                        try:
                            from operations.manage_operations import cancel_pending_order
                            if cancel_pending_order(order.ticket, self.app.logger):
                                success_count += 1
                        except Exception as e:
                            self.app._log_error(f"Error cancelando orden {order.ticket}: {e}")
                
                # Verificar resultado
                import time
                time.sleep(2)
                
                remaining = 0
                if mt5.positions_get(symbol=self.app.simulation_instance.symbol):
                    remaining += len(mt5.positions_get(symbol=self.app.simulation_instance.symbol))
                if mt5.orders_get(symbol=self.app.simulation_instance.symbol):
                    remaining += len(mt5.orders_get(symbol=self.app.simulation_instance.symbol))
                
                # Programar callback en hilo principal
                self.app.root.after(0, lambda: self._handle_close_result(remaining == 0, remaining))
                
            except Exception as e:
                self.app._log_error(f"Error crítico en cierre: {e}")
                self.app.root.after(0, lambda: self._handle_close_result(False, -1))
        
        thread = threading.Thread(target=close_operations, daemon=True)
        thread.start()

    def _handle_close_result(self, success, remaining):
        """Maneja el resultado del cierre de operaciones."""
        if success:
            self.app._log_success("Todas las operaciones han sido cerradas exitosamente")
            self._finalize_exit()
        else:
            if remaining > 0:
                messagebox.showerror(
                    "Error al cerrar operaciones",
                    f"No se pudieron cerrar todas las operaciones.\n\n"
                    f"Quedan {remaining} operación(es) abiertas.\n\n"
                    "La aplicación no se cerrará para evitar pérdidas.\n"
                    "Por favor, cierre manualmente las operaciones restantes.",
                    icon='error'
                )
            else:
                self.app._log_error("Error crítico durante el cierre de operaciones")
    
    def _finalize_exit(self):
        """Finaliza el cierre de la aplicación."""
        try:
            self.save_session_log()
            self.app._log_success("Log de sesión guardado correctamente")
        except Exception as e:
            self.app._log_error(f"Error al guardar log de sesión: {e}")
        
        if self.app.simulation_running:
            self.app.simulation_running = False
        
        self.app.prefs_manager.save(
            symbol=self.app.symbol_var.get(), 
            timeframe=self.app.timeframe_var.get()
        )
        
        self.app.root.destroy()
        print("Saliendo del programa...")
        os._exit(0)

    def on_exit(self):
        """Maneja el cierre de la aplicación de forma segura con threading."""
        if self.app.simulation_running and self.app.simulation_instance:
            try:
                open_positions = mt5.positions_get(symbol=self.app.simulation_instance.symbol)
                pending_orders = mt5.orders_get(symbol=self.app.simulation_instance.symbol)
                
                total_operations = 0
                if open_positions:
                    total_operations += len(open_positions)
                if pending_orders:
                    total_operations += len(pending_orders)
                
                if total_operations > 0:
                    response = messagebox.askyesnocancel(
                        "Operaciones Abiertas",
                        f"Hay {total_operations} operación(es) abierta(s).\n\n"
                        "¿Desea cerrar todas las operaciones abiertas antes de salir?\n\n"
                        "• Sí: Cerrar todas las operaciones y salir\n"
                        "• No: Mantener operaciones abiertas y salir\n"
                        "• Cancelar: No salir de la aplicación",
                        icon='warning'
                    )
                    
                    if response is None:
                        self.app._log_info("Cierre de aplicación cancelado por el usuario")
                        return
                    
                    elif response:
                        self.app._log_info("Cerrando todas las operaciones antes de salir...")
                        messagebox.showinfo("Cerrando Operaciones", 
                                        "Cerrando operaciones en progreso...\nPor favor espere.")
                        
                        # Usar threading para evitar bloquear UI
                        self._close_operations_in_thread(open_positions, pending_orders)
                        return  # No continuar hasta que termine el hilo
                    
                    else:
                        self.app._log_info("Manteniendo operaciones abiertas al salir")
                
            except Exception as e:
                self.app._log_error(f"Error al verificar operaciones abiertas: {e}")
        
        # Continuar con cierre normal
        self._finalize_exit()