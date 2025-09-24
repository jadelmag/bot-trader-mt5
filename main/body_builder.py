from tkinter import ttk
from gui.body_graphic import BodyGraphic
from gui.body_logger import BodyLogger

def create_body(app):
    """Crea y configura el frame del cuerpo principal y sus componentes."""
    container = ttk.Frame(app.root, padding=(12, 10))
    container.grid(row=1, column=0, sticky="nsew")
    container.columnconfigure(0, weight=1)
    # Split rows: top chart (3x), bottom logger (1x)
    container.rowconfigure(0, weight=3)
    container.rowconfigure(1, weight=1)

    # Bottom: Logger (create it first)
    if BodyLogger is None:
        app.logger = ttk.Frame(container)
        ttk.Label(app.logger, text="Logger no disponible").pack(expand=True, fill="both")
    else:
        app.logger = BodyLogger(container)
    app.logger.grid(row=1, column=0, sticky="nsew", pady=(10, 0))

    # Top: Graphic placeholder (shown until Start MT5 is pressed)
    app.graphic_placeholder = ttk.Frame(container)
    app.graphic_placeholder.grid(row=0, column=0, sticky="nsew")
    placeholder_lbl = ttk.Label(
        app.graphic_placeholder,
        text="Pulsa 'Iniciar MT5' para cargar el gráfico",
        anchor="center",
        font=("Segoe UI", 12),
        foreground="#555",
    )
    placeholder_lbl.pack(expand=True, fill="both")

    # Prepare the graphic but do not show it yet
    if BodyGraphic is None:
        app.graphic = ttk.Frame(container)
        ttk.Label(app.graphic, text="Gráfico no disponible").pack(expand=True, fill="both")
    else:
        # Pass the logger and app instance to the graphic
        app.graphic = BodyGraphic(
            container, 
            app=app, # Pass the whole app instance
            symbol=app.symbol_var.get(), 
            timeframe=app.timeframe_var.get(), 
            bars=300,
            logger=app.logger,  # Pass logger instance
            debug_mode_var=app.debug_mode_var # Pass debug mode variable
        )
    # Do not grid the graphic now; it will be gridded when started

    return container
