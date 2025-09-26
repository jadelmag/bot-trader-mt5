import tkinter as tk
from tkinter import ttk
import MetaTrader5 as mt5
from datetime import datetime
import threading
import time

class OperacionesAbiertasWindow:
    def __init__(self, parent, simulation_instance, logger):
        """
        Ventana modal no bloqueante para mostrar operaciones abiertas.
        
        Args:
            parent: Ventana padre
            simulation_instance: Instancia de la simulación
            logger: Logger para mostrar mensajes
        """
        self.parent = parent
        self.simulation_instance = simulation_instance
        self.logger = logger
        self.window = None
        self.is_running = False
        self.update_thread = None
        self.operations_frame = None
        self.operation_widgets = {}  # Diccionario para almacenar widgets de cada operación
        
        self.create_window()
        self.start_real_time_updates()
    
    def create_window(self):
        """Crea la ventana modal no bloqueante."""
        self.window = tk.Toplevel(self.parent)
        self.window.title("Operaciones Abiertas")
        self.window.geometry("900x500")
        self.window.resizable(True, True)
        
        # Hacer la ventana no bloqueante
        self.window.transient(self.parent)
        self.window.grab_set()
        self.window.grab_release()  # Liberar el grab para hacerla no bloqueante
        
        # Centrar la ventana
        self.center_window()
        
        # Configurar el cierre de la ventana
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Crear el contenido de la ventana
        self.create_content()
        
        # Cargar operaciones iniciales
        self.update_operations()
    
    def center_window(self):
        """Centra la ventana en la pantalla."""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"{width}x{height}+{x}+{y}")
    
    def create_content(self):
        """Crea el contenido de la ventana."""
        # Título centrado
        title_label = ttk.Label(self.window, text="Operaciones Abiertas", 
                               font=("Arial", 16, "bold"))
        title_label.pack(pady=10)
        
        # Frame principal con scrollbar
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Canvas y scrollbar para el contenido scrolleable
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        self.operations_frame = ttk.Frame(canvas)
        
        # Configurar el scrolling
        self.operations_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.operations_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Empaquetar canvas y scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Mensaje cuando no hay operaciones
        self.no_operations_label = ttk.Label(self.operations_frame, 
                                           text="No hay operaciones abiertas", 
                                           font=("Arial", 12))
        self.no_operations_label.pack(pady=20)
    
    def update_operations(self):
        """Actualiza la lista de operaciones abiertas."""
        if not self.simulation_instance:
            return
        
        try:
            # Obtener operaciones abiertas
            open_positions = mt5.positions_get(symbol=self.simulation_instance.symbol)
            
            if not open_positions or len(open_positions) == 0:
                # No hay operaciones, mostrar mensaje
                self.show_no_operations()
                return
            
            # Ocultar mensaje de "no hay operaciones"
            self.no_operations_label.pack_forget()
            
            # Actualizar operaciones existentes y agregar nuevas
            current_tickets = set()
            
            for i, pos in enumerate(open_positions):
                current_tickets.add(pos.ticket)
                
                if pos.ticket in self.operation_widgets:
                    # Actualizar operación existente
                    self.update_operation_widget(pos)
                else:
                    # Crear nueva operación
                    self.create_operation_widget(pos, i)
            
            # Eliminar operaciones que ya no existen
            tickets_to_remove = set(self.operation_widgets.keys()) - current_tickets
            for ticket in tickets_to_remove:
                self.remove_operation_widget(ticket)
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error al actualizar operaciones: {e}")
    
    def show_no_operations(self):
        """Muestra el mensaje cuando no hay operaciones."""
        # Limpiar todas las operaciones
        for ticket in list(self.operation_widgets.keys()):
            self.remove_operation_widget(ticket)
        
        # Mostrar mensaje
        self.no_operations_label.pack(pady=20)
    
    def create_operation_widget(self, position, index):
        """Crea un widget para mostrar una operación."""
        ticket = position.ticket
        
        # Frame para esta operación
        op_frame = ttk.LabelFrame(self.operations_frame, 
                                 text=f"Operación #{ticket}", 
                                 padding=10)
        op_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Frame para la información
        info_frame = ttk.Frame(op_frame)
        info_frame.pack(fill=tk.X)
        
        # Configurar grid
        info_frame.columnconfigure(1, weight=1)
        info_frame.columnconfigure(3, weight=1)
        info_frame.columnconfigure(5, weight=1)
        
        # Información de la operación
        ttk.Label(info_frame, text="Ticket:").grid(row=0, column=0, sticky="w", padx=(0, 5))
        ticket_label = ttk.Label(info_frame, text=str(ticket), font=("Arial", 10, "bold"))
        ticket_label.grid(row=0, column=1, sticky="w", padx=(0, 20))
        
        ttk.Label(info_frame, text="Volumen:").grid(row=0, column=2, sticky="w", padx=(0, 5))
        volume_label = ttk.Label(info_frame, text=f"{position.volume:.2f}")
        volume_label.grid(row=0, column=3, sticky="w", padx=(0, 20))
        
        ttk.Label(info_frame, text="P/L:").grid(row=0, column=4, sticky="w", padx=(0, 5))
        pl_label = ttk.Label(info_frame, text=f"{position.profit:.2f} $")
        pl_label.grid(row=0, column=5, sticky="w")
        
        # Segunda fila
        ttk.Label(info_frame, text="Tipo:").grid(row=1, column=0, sticky="w", padx=(0, 5))
        trade_type = 'Long' if position.type == mt5.POSITION_TYPE_BUY else 'Short'
        type_label = ttk.Label(info_frame, text=trade_type)
        type_label.grid(row=1, column=1, sticky="w", padx=(0, 20))
        
        ttk.Label(info_frame, text="Precio apertura:").grid(row=1, column=2, sticky="w", padx=(0, 5))
        open_price_label = ttk.Label(info_frame, text=f"{position.price_open:.5f}")
        open_price_label.grid(row=1, column=3, sticky="w", padx=(0, 20))
        
        ttk.Label(info_frame, text="Precio actual:").grid(row=1, column=4, sticky="w", padx=(0, 5))
        current_price_label = ttk.Label(info_frame, text="Cargando...", 
                                       font=("Arial", 10, "bold"))
        current_price_label.grid(row=1, column=5, sticky="w")
        
        # Botón cerrar operación
        button_frame = ttk.Frame(op_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        close_btn = ttk.Button(button_frame, text="Cerrar Operación",
                              command=lambda t=ticket: self.close_operation(t))
        close_btn.pack(side=tk.RIGHT)
        
        # Guardar referencias a los widgets
        self.operation_widgets[ticket] = {
            'frame': op_frame,
            'pl_label': pl_label,
            'current_price_label': current_price_label,
            'position': position
        }
    
    def update_operation_widget(self, position):
        """Actualiza los datos de una operación existente."""
        ticket = position.ticket
        if ticket not in self.operation_widgets:
            return
        
        widgets = self.operation_widgets[ticket]
        
        # Actualizar P/L
        widgets['pl_label'].config(text=f"{position.profit:.2f} $")
        
        # Actualizar color del P/L
        if position.profit >= 0:
            widgets['pl_label'].config(foreground="green")
        else:
            widgets['pl_label'].config(foreground="red")
        
        # Actualizar precio actual
        try:
            symbol = position.symbol
            tick = mt5.symbol_info_tick(symbol)
            if tick:
                if position.type == mt5.POSITION_TYPE_BUY:
                    current_price = tick.bid
                else:
                    current_price = tick.ask
                
                widgets['current_price_label'].config(text=f"{current_price:.5f}")
            else:
                widgets['current_price_label'].config(text="N/A")
        except Exception as e:
            widgets['current_price_label'].config(text="Error")
        
        # Actualizar posición almacenada
        widgets['position'] = position
    
    def remove_operation_widget(self, ticket):
        """Elimina el widget de una operación."""
        if ticket in self.operation_widgets:
            self.operation_widgets[ticket]['frame'].destroy()
            del self.operation_widgets[ticket]
    
    def close_operation(self, ticket):
        """Cierra una operación específica."""
        try:
            # Importar la función de cerrar operación
            from operations.close_operations import close_single_operation
            
            # Cerrar la operación
            success = close_single_operation(ticket, self.logger)
            
            if success:
                if self.logger:
                    self.logger.success(f"Operación {ticket} cerrada exitosamente")
            else:
                if self.logger:
                    self.logger.error(f"Error al cerrar la operación {ticket}")
                    
        except ImportError:
            if self.logger:
                self.logger.error("Módulo close_operations no disponible")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error al cerrar operación {ticket}: {e}")
    
    def start_real_time_updates(self):
        """Inicia las actualizaciones en tiempo real."""
        self.is_running = True
        self.update_thread = threading.Thread(target=self.update_loop, daemon=True)
        self.update_thread.start()
    
    def update_loop(self):
        """Bucle de actualización en tiempo real."""
        while self.is_running:
            try:
                # Programar actualización en el hilo principal
                if self.window and self.window.winfo_exists():
                    self.window.after_idle(self.update_operations)
                else:
                    break
                    
                # Esperar 1 segundo antes de la siguiente actualización
                time.sleep(1)
                
            except Exception as e:
                if self.logger:
                    self.window.after_idle(lambda: self.logger.error(f"Error en actualización: {e}"))
                break
    
    def on_close(self):
        """Maneja el cierre de la ventana."""
        self.is_running = False
        if self.update_thread and self.update_thread.is_alive():
            self.update_thread.join(timeout=1)
        
        if self.window:
            self.window.destroy()
    
    def show(self):
        """Muestra la ventana."""
        if self.window:
            self.window.deiconify()
            self.window.lift()
            self.window.focus_force()