import tkinter as tk
from tkinter import ttk
import MetaTrader5 as mt5
from datetime import datetime
import threading
import time

class CerrarOperacionesWindow:
    def __init__(self, parent, simulation_instance, logger):
        self.parent = parent
        self.simulation_instance = simulation_instance
        self.logger = logger
        self.window = None
        self.is_running = False
        self.update_thread = None
        self.operations_frame = None
        self.operation_widgets = {}
        
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
    
    def create_content(self):
        # Título centrado
        title_label = ttk.Label(self.window, text="Operaciones Abiertas", 
                               font=("Arial", 18, "bold"))
        title_label.pack(pady=15)
        
        # Frame principal con scrollbar
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        # Canvas y scrollbar
        canvas = tk.Canvas(main_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        self.operations_frame = ttk.Frame(canvas)
        
        self.operations_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.operations_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Mouse wheel support
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Mensaje cuando no hay operaciones
        self.no_operations_label = ttk.Label(self.operations_frame, 
                                           text="No hay operaciones abiertas", 
                                           font=("Arial", 14))
        self.no_operations_label.pack(pady=30)
    
    def update_operations(self):
        if not self.simulation_instance:
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
        ttk.Label(row1, text=f"Volumen: {operation.volume:.2f}", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=(0, 20))
        
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
        
        # FILA 2: Precio apertura | Precio actual
        row2 = ttk.Frame(op_frame)
        row2.pack(fill=tk.X, pady=5)
        
        open_price = operation.price_open
        ttk.Label(row2, text=f"Precio apertura: {open_price:.5f}", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=(0, 40))
        
        current_price_label = ttk.Label(row2, text="Precio actual: Cargando...", 
                                       font=("Arial", 9, "bold"), foreground="blue")
        current_price_label.pack(side=tk.LEFT)
        
        # FILA 3: Botones
        row3 = ttk.Frame(op_frame)
        row3.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(row3, text="Cerrar Operación",
                  command=lambda t=ticket, ot=op_type: self.close_operation(t, ot)).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(row3, text="Modificar Operación",
                  command=lambda t=ticket, ot=op_type: self.modify_operation(t, ot)).pack(side=tk.LEFT, padx=(0, 10))
        
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
        ticket = operation.ticket
        if ticket not in self.operation_widgets:
            return
        
        widgets = self.operation_widgets[ticket]
        
        # Actualizar P/L
        if op_type == 'position':
            widgets['pl_label'].config(text=f"P/L: {operation.profit:.2f} $")
            widgets['pl_label'].config(foreground="green" if operation.profit >= 0 else "red")
        
        # Actualizar precio actual
        try:
            tick = mt5.symbol_info_tick(operation.symbol)
            if tick:
                if op_type == 'position':
                    current_price = tick.bid if operation.type == mt5.POSITION_TYPE_BUY else tick.ask
                else:
                    current_price = (tick.bid + tick.ask) / 2
                
                widgets['current_price_label'].config(text=f"Precio actual: {current_price:.5f}")
            else:
                widgets['current_price_label'].config(text="Precio actual: N/A")
        except:
            widgets['current_price_label'].config(text="Precio actual: Error")
        
        widgets['operation'] = operation
        widgets['op_type'] = op_type
    
    def remove_operation_widget(self, ticket):
        if ticket in self.operation_widgets:
            self.operation_widgets[ticket]['frame'].destroy()
            del self.operation_widgets[ticket]
    
    def close_operation(self, ticket, op_type):
        try:
            from operations.manage_operations import close_single_operation
            success = close_single_operation(ticket, op_type, self.logger)
            
            if success and self.logger:
                self.logger.success(f"{'Posición' if op_type == 'position' else 'Orden'} {ticket} cerrada exitosamente")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error al cerrar operación {ticket}: {e}")
    
    def modify_operation(self, ticket, op_type):
        if self.logger:
            self.logger.log(f"Función modificar operación {ticket} - En desarrollo")
    
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
                if self.logger:
                    self.window.after_idle(lambda: self.logger.error(f"Error en actualización: {e}"))
                break
    
    def on_close(self):
        self.is_running = False
        if self.update_thread and self.update_thread.is_alive():
            self.update_thread.join(timeout=1)
        if self.window:
            self.window.destroy()