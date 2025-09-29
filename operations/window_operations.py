import tkinter as tk
from tkinter import ttk
import MetaTrader5 as mt5
from datetime import datetime
import threading
import time
from simulation.key_list import get_name_for_id

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
        self.canvas = None  # Referencia al canvas para scroll/limpieza

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
    
    def parse_strategy_info(self, comment):
        """Extrae información de la estrategia desde el comentario de la operación."""
        if not comment or comment == "Bot-Simulation":
            return "MANUAL", "Operación Manual"
        
        comment_clean = comment.strip().lower()

        keyIDComment = comment_clean.split('-')[1]
        strategy_name = get_name_for_id(int(keyIDComment))
        
        # Detectar FOREX por prefijo o palabras clave
        if (strategy_name.startswith('forex_') or 
            any(forex_word in strategy_name for forex_word in 
                ['forex', 'ema', 'rsi', 'macd', 'bollinger', 'ichimoku', 'stoch', 'atr', 'sma', 'strategy'])):
            strategy_type = "FOREX"
            # Limpiar y formatear nombre
            strategy_name = strategy_name.replace('forex_', '').replace('_', ' ')
        
        # Detectar CANDLE por prefijo o patrones conocidos
        elif (strategy_name.startswith('candle_') or 
            any(candle_word in strategy_name for candle_word in 
                ['candle', 'doji', 'hammer', 'engulf', 'star', 'harami', 'piercing', 'dark'])):
            strategy_type = "CANDLE"
            # Limpiar y formatear nombre
            strategy_name = strategy_name.replace('candle_', '').replace('_', ' ').title()
            if not strategy_name or strategy_name == ' ':
                strategy_name = "Patrón de Vela"
        
        else:
            strategy_type = "MANUAL"
            strategy_name = comment.strip() if comment.strip() else "Operación Manual"
        
        return strategy_type, strategy_name

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
                                           font=("Arial", 12))
        self.no_operations_label.pack(pady=20)
    
    def update_operations(self):
        """Actualiza la lista de operaciones abiertas."""
        if not self.simulation_instance:
            return
        # Evitar actualizar si la ventana ya no existe
        if not self.window or not self.window.winfo_exists():
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

        except tk.TclError:
            # Widgets/ventana destruidos durante la actualización
            return        
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
        
        # Tercera fila - Información de estrategia
        strategy_type, strategy_name = self.parse_strategy_info(position.comment)
        strategy_color = "purple" if strategy_type == "FOREX" else "orange" if strategy_type == "CANDLE" else "gray"

        ttk.Label(info_frame, text="Tipo:").grid(row=2, column=0, sticky="w", padx=(0, 5))
        strategy_type_label = ttk.Label(info_frame, text=strategy_type, foreground=strategy_color, font=("Arial", 10, "bold"))
        strategy_type_label.grid(row=2, column=1, sticky="w", padx=(0, 20))

        ttk.Label(info_frame, text="Nombre:").grid(row=2, column=2, sticky="w", padx=(0, 5))
        strategy_name_label = ttk.Label(info_frame, text=strategy_name, foreground=strategy_color, font=("Arial", 10, "bold"))
        strategy_name_label.grid(row=2, column=3, columnspan=3, sticky="w", padx=(0, 20))

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
        try:
            # Comprobar existencia de widgets antes de configurar
            if not widgets['pl_label'].winfo_exists() or not widgets['current_price_label'].winfo_exists():
                return

            # Actualizar P/L y color
            widgets['pl_label'].config(text=f"{position.profit:.2f} $")
            widgets['pl_label'].config(foreground="green" if position.profit >= 0 else "red")

            # Actualizar precio actual
            tick = mt5.symbol_info_tick(position.symbol)
            if tick:
                current_price = tick.bid if position.type == mt5.POSITION_TYPE_BUY else tick.ask
                widgets['current_price_label'].config(text=f"{current_price:.5f}")
            else:
                widgets['current_price_label'].config(text="N/A")
        except tk.TclError:
            # Algún widget fue destruido mientras se actualizaba
            return
        except Exception:
            try:
                if widgets['current_price_label'].winfo_exists():
                    widgets['current_price_label'].config(text="Error")
            except tk.TclError:
                pass

        # Actualizar posición almacenada
        widgets['position'] = position
    
    def remove_operation_widget(self, ticket):
        """Elimina el widget de una operación."""
        if ticket in self.operation_widgets:
            try:
                if self.operation_widgets[ticket]['frame'].winfo_exists():
                    self.operation_widgets[ticket]['frame'].destroy()
            except tk.TclError:
                pass
            finally:
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
    
    def show(self):
        """Muestra la ventana."""
        if self.window:
            self.window.deiconify()
            self.window.lift()
            self.window.focus_force()