from tkinter import ttk
from gui.body_graphic import BodyGraphic
from gui.body_logger import BodyLogger
from gui.body_rsi import BodyRSI
from gui.body_atr import BodyATR
from gui.body_macd import BodyMACD

def create_body(app):
    """Crea y configura el frame del cuerpo principal y sus componentes."""
    container = ttk.Frame(app.root, padding=(12, 10))
    container.grid(row=1, column=0, sticky="nsew")
    container.columnconfigure(0, weight=1)
    
    # Split rows: top chart (3x), RSI (1x), ATR (1x), MACD (1x), logger (1x)
    container.rowconfigure(0, weight=3)  # BodyGraphic
    container.rowconfigure(1, weight=1)  # BodyRSI
    container.rowconfigure(2, weight=1)  # BodyATR
    container.rowconfigure(3, weight=1)  # BodyMACD
    container.rowconfigure(4, weight=1)  # BodyLogger

    # Bottom: Logger
    if BodyLogger is None:
        app.logger = ttk.Frame(container)
        ttk.Label(app.logger, text="Logger no disponible").pack(expand=True, fill="both")
    else:
        app.logger = BodyLogger(container)
    app.logger.grid(row=4, column=0, sticky="nsew", pady=(10, 0))

    # Middle: RSI Chart
    if BodyRSI is None:
        app.rsi_chart = ttk.Frame(container)
        ttk.Label(app.rsi_chart, text="RSI no disponible").pack(expand=True, fill="both")
    else:
        app.rsi_chart = BodyRSI(
            container,
            app=app,
            symbol=app.symbol_var.get(),
            timeframe=app.timeframe_var.get(),
            bars=300,
            logger=app.logger,
            debug_mode_var=app.debug_mode_var
        )
    app.rsi_chart.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
    
    # Middle 2: ATR Chart
    if BodyATR is None:
        app.atr_chart = ttk.Frame(container)
        ttk.Label(app.atr_chart, text="ATR no disponible").pack(expand=True, fill="both")
    else:
        app.atr_chart = BodyATR(
            container,
            app=app,
            symbol=app.symbol_var.get(),
            timeframe=app.timeframe_var.get(),
            bars=300,
            logger=app.logger,
            debug_mode_var=app.debug_mode_var
        )
    app.atr_chart.grid(row=2, column=0, sticky="nsew", pady=(10, 0))

    # Middle 3: MACD Chart
    if BodyMACD is None:
        app.macd_chart = ttk.Frame(container)
        ttk.Label(app.macd_chart, text="MACD no disponible").pack(expand=True, fill="both")
    else:
        app.macd_chart = BodyMACD(
            container,
            app=app,
            symbol=app.symbol_var.get(),
            timeframe=app.timeframe_var.get(),
            bars=300,
            logger=app.logger,
            debug_mode_var=app.debug_mode_var
        )
    app.macd_chart.grid(row=3, column=0, sticky="nsew", pady=(10, 0))

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