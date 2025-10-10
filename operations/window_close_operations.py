import tkinter as tk
from tkinter import ttk
import MetaTrader5 as mt5
from datetime import datetime
import threading
import time
from simulation.key_list import get_name_for_id

class CerrarOperacionesWindow:
    def __init__(self, parent, simulation_instance, logger):
        self.parent = parent
        self.simulation_instance = simulation_instance
        self.logger = logger
        self.window = None
        self.is_running = False
        self.update_thread = None
        self.operations_frame = None
        self.operation_widgets = {}  # Diccionario para almacenar widgets de cada operación
        self.canvas = None  # Referencia al canvas para el manejo del scroll
        
        self.create_window()
        self.start_real_time_updates()
    
    def create_window(self):
        self.window = tk.Toplevel(self.parent)
        self.window.title("Gestionar Operaciones")
        self.window.geometry("1000x600")
        self.window.resizable(True, True)
        
        # Hacer no bloqueante
        self.window.transient(self.parent)
        self.window.grab_set()
        self.window.grab_release()
        
        self.center_window()
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
        self.create_content()
        self.update_operations()
    
    def center_window(self):
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"{width}x{height}+{x}+{y}")
    
    def parse_strategy_info(self, comment):
        """Extrae información de la estrategia desde el comentario de la operación."""
        if not comment or comment == "Bot-Simulation":
            return "MANUAL", "Operación Manual"
        
        comment_clean = comment.strip()

        try:
            if comment_clean.startswith('key-') and '-bot-' in comment_clean.lower():
                parts = comment_clean.split('-')
                if len(parts) > 1:
                    keyIDComment = parts[1]
                    strategy_name = get_name_for_id(int(keyIDComment))
                else:
                    return "MANUAL", comment
            else:
                return "MANUAL", comment
        except (ValueError, IndexError):
            return "MANUAL", comment
        
        # Determinar el tipo basado en prefijos conocidos
        if any(forex_indicator in strategy_name.lower() for forex_indicator in 
            ['ema', 'rsi', 'macd', 'bollinger', 'ichimoku', 'stoch', 'atr', 'sma']):
            strategy_type = "FOREX"
            strategy_name = strategy_name.replace('forex_', '').replace('_', ' ').title()
        elif any(candle_pattern in strategy_name.lower() for candle_pattern in 
                ['doji', 'hammer', 'engulf', 'star', 'harami', 'piercing', 'dark']):
            strategy_type = "CANDLE"
            strategy_name = strategy_name.replace('candle_', '').replace('_', ' ').title()
        else:
            strategy_type = "MANUAL"
            strategy_name = strategy_name if strategy_name else "Operación Manual"
        
        return strategy_type, strategy_name

    def create_content(self):
        # Título centrado
        title_label = ttk.Label(self.window, text="Operaciones Abiertas", 
                               font=("Arial", 18, "bold"))
        title_label.pack(pady=15)
        
        # Frame principal con scrollbar
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        # Canvas y scrollbar para el contenido scrolleable
        self.canvas = tk.Canvas(main_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.canvas.yview)
        self.operations_frame = ttk.Frame(self.canvas)

        # Configurar el scrolling
        self.operations_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.operations_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        # Soporte de rueda del ratón con comprobaciones
        def _on_mousewheel(event):
            try:
                if self.canvas and self.canvas.winfo_exists():
                    self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except tk.TclError:
                # Widget destruido; ignorar
                pass
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error en scroll: {e}")

        # Enlazar a widgets específicos (no bind_all)
        self.canvas.bind("<MouseWheel>", _on_mousewheel)
        self.operations_frame.bind("<MouseWheel>", _on_mousewheel)

        # Empaquetar
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Mensaje cuando no hay operaciones
        self.no_operations_label = ttk.Label(self.operations_frame, 
                                           text="No hay operaciones abiertas", 
                                           font=("Arial", 14))
        self.no_operations_label.pack(pady=30)
    
    def update_operations(self):
        """Actualiza la lista de operaciones abiertas."""
        if not self.simulation_instance:
            return
        # Evitar actualizar si la ventana ya no existe
        if not self.window or not self.window.winfo_exists():
            return
        
        try:
            # Obtener posiciones y órdenes
            open_positions = mt5.positions_get(symbol=self.simulation_instance.symbol)
            pending_orders = mt5.orders_get(symbol=self.simulation_instance.symbol)
            
            all_operations = []
            if open_positions:
                all_operations.extend([(pos, 'position') for pos in open_positions])
            if pending_orders:
                all_operations.extend([(order, 'order') for order in pending_orders])
            
            # Evitar actualizar si la ventana ya no existe
            if not self.window or not self.window.winfo_exists():
                return
            if not all_operations:
                self.show_no_operations()
                return
            
            self.no_operations_label.pack_forget()
            
            current_tickets = set()
            for operation, op_type in all_operations:
                ticket = operation.ticket
                current_tickets.add(ticket)
                
                if ticket in self.operation_widgets:
                    self.update_operation_widget(operation, op_type)
                else:
                    self.create_operation_widget(operation, op_type)
            
            # Eliminar operaciones que ya no existen
            tickets_to_remove = set(self.operation_widgets.keys()) - current_tickets
            for ticket in tickets_to_remove:
                self.remove_operation_widget(ticket)
                
        except tk.TclError:
            # Widgets/ventana destruidos durante la actualización
            return
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error al actualizar operaciones: {e}")
    
    def show_no_operations(self):
        for ticket in list(self.operation_widgets.keys()):
            self.remove_operation_widget(ticket)
        self.no_operations_label.pack(pady=30)
    
    def create_operation_widget(self, operation, op_type):
        ticket = operation.ticket
        
        # Frame principal
        op_frame = ttk.LabelFrame(self.operations_frame, 
                                 text=f"{'Posición' if op_type == 'position' else 'Orden Pendiente'} #{ticket}", 
                                 padding=15)
        op_frame.pack(fill=tk.X, padx=10, pady=8)
        
        # FILA 1: Ticket | Volumen | P/L | Tipo
        row1 = ttk.Frame(op_frame)
        row1.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(row1, text=f"Ticket: {ticket}", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=(0, 20))
        ttk.Label(row1, text=f"Volumen: {operation.volume}", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=(0, 20))
        
        if op_type == 'position':
            pl_text = f"P/L: {operation.profit:.2f} $"
            pl_color = "green" if operation.profit >= 0 else "red"
            trade_type = 'Long' if operation.type == mt5.POSITION_TYPE_BUY else 'Short'
        else:
            pl_text = "P/L: Pendiente"
            pl_color = "orange"
            trade_type = 'Buy Order' if operation.type in [mt5.ORDER_TYPE_BUY_LIMIT, mt5.ORDER_TYPE_BUY_STOP] else 'Sell Order'
        
        pl_label = ttk.Label(row1, text=pl_text, foreground=pl_color, font=("Arial", 9, "bold"))
        pl_label.pack(side=tk.LEFT, padx=(0, 20))
        
        ttk.Label(row1, text=f"Tipo: {trade_type}", font=("Arial", 9, "bold")).pack(side=tk.LEFT)
        
        # FILA 2: Precio apertura | Precio actual | Estrategia
        row2 = ttk.Frame(op_frame)
        row2.pack(fill=tk.X, pady=5)

        open_price = operation.price_open
        ttk.Label(row2, text=f"Precio apertura: {open_price:.5f}", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=(0, 20))

        current_price_label = ttk.Label(row2, text="Precio actual: Cargando...", 
                                    font=("Arial", 9, "bold"), foreground="blue")
        current_price_label.pack(side=tk.LEFT, padx=(0, 20))

        # Agregar información de estrategia
        # Tercera fila - Información de estrategia
        strategy_type, strategy_name = self.parse_strategy_info(operation.comment)
        strategy_color = "purple" if strategy_type == "FOREX" else "orange" if strategy_type == "CANDLE" else "gray"

        # Crear una nueva fila para la estrategia
        strategy_row = ttk.Frame(op_frame)
        strategy_row.pack(fill=tk.X, pady=5)

        ttk.Label(strategy_row, text=f"Tipo: {strategy_type}", foreground=strategy_color, font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=(0, 20))
        ttk.Label(strategy_row, text=f"Nombre: {strategy_name}", foreground=strategy_color, font=("Arial", 9, "bold")).pack(side=tk.LEFT)

        # FILA 3: Botones
        row3 = ttk.Frame(op_frame)
        row3.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(row3, text="Cerrar Operación",
                  command=lambda t=ticket, ot=op_type: self.close_operation(t, ot)).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(row3, text="Modificar Operación",
                  command=lambda t=ticket, ot=op_type: self.show_modify_dialog(t, ot)).pack(side=tk.LEFT, padx=(0, 10))
        
        cancel_btn = None
        if op_type == 'order':
            cancel_btn = ttk.Button(row3, text="Cancelar Operación",
                                   command=lambda t=ticket: self.cancel_order(t))
            cancel_btn.pack(side=tk.LEFT)
        
        # Guardar referencias
        self.operation_widgets[ticket] = {
            'frame': op_frame,
            'pl_label': pl_label,
            'current_price_label': current_price_label,
            'operation': operation,
            'op_type': op_type
        }
    
    def update_operation_widget(self, operation, op_type):
        """
        Actualiza el widget de una operación existente.
        """
        ticket = operation.ticket
        if ticket not in self.operation_widgets:
            return
        
        widgets = self.operation_widgets[ticket]
        try:
            # Comprobar existencia de widgets antes de configurar
            if not widgets['pl_label'].winfo_exists() or not widgets['current_price_label'].winfo_exists():
                return

            # Actualizar P/L
            if op_type == 'position':
                widgets['pl_label'].config(text=f"P/L: {operation.profit:.2f} $")
                widgets['pl_label'].config(foreground="green" if operation.profit >= 0 else "red")

            # Actualizar precio actual
            tick = mt5.symbol_info_tick(operation.symbol)
            if tick:
                if op_type == 'position':
                    current_price = tick.bid if operation.type == mt5.POSITION_TYPE_BUY else tick.ask
                else:
                    current_price = (tick.bid + tick.ask) / 2
                widgets['current_price_label'].config(text=f"Precio actual: {current_price:.5f}")
            else:
                widgets['current_price_label'].config(text="Precio actual: N/A")
        except tk.TclError:
            # Algún widget fue destruido mientras se actualizaba
            return
        except Exception:
            try:
                if widgets['current_price_label'].winfo_exists():
                    widgets['current_price_label'].config(text="Precio actual: Error")
            except tk.TclError:
                pass

        widgets['operation'] = operation
        widgets['op_type'] = op_type
    
    def remove_operation_widget(self, ticket):
        if ticket in self.operation_widgets:
            try:
                if self.operation_widgets[ticket]['frame'].winfo_exists():
                    self.operation_widgets[ticket]['frame'].destroy()
            except tk.TclError:
                pass
            finally:
                del self.operation_widgets[ticket]
    
    def close_operation(self, ticket, op_type):
        try:
            from operations.manage_operations import close_single_operation
            success = close_single_operation(ticket, op_type, self.logger)
            
            if success and self.logger:
                self.logger.success(f"{'Posición' if op_type == 'position' else 'Orden'} {ticket} cerrada exitosamente")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error al cerrar la operación {ticket}: {e}")
    
    def modify_operation(self, ticket, op_type, sl=None, tp=None, comment=None):
        """
        Modifica una operación existente en MT5.
        
        Args:
            ticket: Número de ticket de la operación a modificar
            op_type: Tipo de operación ('position' o 'order')
            sl: Nuevo Stop Loss (None para mantener el actual)
            tp: Nuevo Take Profit (None para mantener el actual)
            comment: Nuevo comentario (None para mantener el actual)
            
        Returns:
            bool: True si la modificación fue exitosa, False en caso contrario
        """
        if not mt5 or not mt5.terminal_info():
            if self.logger:
                self.logger.error(f"[TRADE-ERROR] MT5 no está conectado.")
            return False
        
        # Obtener información de la posición
        position = mt5.positions_get(ticket=ticket)
        if not position:
            if self.logger:
                self.logger.error(f"[TRADE-ERROR] No se encontró la posición {ticket}")
            return False
        
        position = position[0]
        
        # Preparar la solicitud de modificación
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "symbol": position.symbol,
            "magic": position.magic,
        }
        
        # Añadir los parámetros que se quieren modificar
        if sl is not None:
            request["sl"] = sl
        else:
            request["sl"] = position.sl
            
        if tp is not None:
            request["tp"] = tp
        else:
            request["tp"] = position.tp
            
        # Enviar la solicitud
        result = mt5.order_send(request)
        
        if result is None:
            if self.logger:
                self.logger.error(f"[TRADE-ERROR] mt5.order_send devolvió None. last_error={mt5.last_error()}")
            return False
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            from metatrader.metatrader import obtener_mensaje_error
            if self.logger:
                self.logger.error(f"[TRADE-ERROR] Modificación falló, retcode={result.retcode} ({obtener_mensaje_error(result.retcode)})")
            return False
        
        # Guardar los nuevos SL/TP en el tracking
        if hasattr(self.simulation_instance, 'positions_sl_tp') and ticket in self.simulation_instance.positions_sl_tp:
            self.simulation_instance.positions_sl_tp[ticket].update({
                'sl': sl if sl is not None else position.sl,
                'tp': tp if tp is not None else position.tp
            })
        
        # Registrar la modificación
        if self.logger:
            self.logger.success(f"[TRADE] ✏️ Modificada operación #{ticket} | SL: {sl} | TP: {tp}")
        
        # Actualizar la operación en el widget
        if ticket in self.operation_widgets:
            self.operation_widgets[ticket]['operation'] = position
            
        return True

    def cancel_order(self, ticket):
        try:
            from operations.manage_operations import cancel_pending_order
            success = cancel_pending_order(ticket, self.logger)
            
            if success and self.logger:
                self.logger.success(f"Orden {ticket} cancelada exitosamente")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error al cancelar orden {ticket}: {e}")
    
    def start_real_time_updates(self):
        self.is_running = True
        self.update_thread = threading.Thread(target=self.update_loop, daemon=True)
        self.update_thread.start()
    
    def update_loop(self):
        while self.is_running:
            try:
                if self.window and self.window.winfo_exists():
                    self.window.after_idle(self.update_operations)
                else:
                    break
                time.sleep(1)
            except Exception as e:
                if self.logger and self.window and self.window.winfo_exists():
                    self.window.after_idle(lambda: self.logger.error(f"Error en actualización: {e}"))
                break
    
    def on_close(self):
        """Maneja el cierre de la ventana."""
        self.is_running = False
        if self.update_thread and self.update_thread.is_alive():
            self.update_thread.join(timeout=1)

        # Limpiar eventos de scroll
        if self.canvas:
            try:
                self.canvas.unbind("<MouseWheel>")
            except Exception:
                pass
        if self.operations_frame:
            try:
                self.operations_frame.unbind("<MouseWheel>")
            except Exception:
                pass

        if self.window:
            self.window.destroy()

        # Limpiar referencias
        self.canvas = None
        self.operations_frame = None

    def show_modify_dialog(self, ticket, op_type):
        """Muestra un diálogo para modificar SL/TP y luego llama a modify_operation."""
        operation = self.operation_widgets[ticket]['operation']
        
        # Crear una ventana modal
        dialog = tk.Toplevel(self.window)
        dialog.title(f"Modificar Operación #{ticket}")
        dialog.grab_set()  # Hacer modal
        dialog.transient(self.window)
        
        # Centro de la ventana principal
        dialog.geometry("400x250")
        x = self.window.winfo_x() + (self.window.winfo_width() - 400) // 2
        y = self.window.winfo_y() + (self.window.winfo_height() - 250) // 2
        dialog.geometry(f"+{x}+{y}")
        
        # Campos para SL/TP
        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        current_sl = operation.sl if hasattr(operation, 'sl') else 0
        current_tp = operation.tp if hasattr(operation, 'tp') else 0
        
        # Variables para los nuevos valores
        sl_var = tk.StringVar(value=str(current_sl) if current_sl else "")
        tp_var = tk.StringVar(value=str(current_tp) if current_tp else "")
        
        # Campos de entrada
        ttk.Label(frame, text="Stop Loss:").grid(row=0, column=0, sticky="w", pady=5)
        sl_entry = ttk.Entry(frame, textvariable=sl_var)
        sl_entry.grid(row=0, column=1, sticky="we", padx=5, pady=5)
        
        ttk.Label(frame, text="Take Profit:").grid(row=1, column=0, sticky="w", pady=5)
        tp_entry = ttk.Entry(frame, textvariable=tp_var)
        tp_entry.grid(row=1, column=1, sticky="we", padx=5, pady=5)
        
        # Botones
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=20)
        
        def on_apply():
            try:
                # Convertir a float o None
                sl = float(sl_var.get()) if sl_var.get().strip() else None
                tp = float(tp_var.get()) if tp_var.get().strip() else None
                
                # Llamar a modify_operation con los nuevos valores
                success = self.modify_operation(ticket, op_type, sl, tp)
                if success:
                    dialog.destroy()
            except ValueError:
                tk.messagebox.showerror("Error", "Por favor, introduzca valores numéricos válidos.", parent=dialog)
        
        ttk.Button(btn_frame, text="Aplicar", command=on_apply).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancelar", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
