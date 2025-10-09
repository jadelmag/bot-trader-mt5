import tkinter as tk
from tkinter import ttk

def create_header(app):
    """Crea y configura el frame del encabezado y todos sus widgets."""
    header = ttk.Frame(app.root, padding=(16, 10))
    header.grid(row=0, column=0, sticky="ew")

    # --- Botón de Herramientas de Análisis (Columna 0) ---
    app.analysis_tools_btn = ttk.Menubutton(header, text="Herramientas")
    app.analysis_tools_btn.grid(row=0, column=0, padx=(6, 12))
    tools_menu = tk.Menu(app.analysis_tools_btn, tearoff=False)
    app.analysis_tools_btn["menu"] = tools_menu
    tools_menu.add_command(label="Aplicar estrategias", command=app.action_handler.apply_strategies_action)
    tools_menu.add_command(label="Detectar patrones de velas", command=app.action_handler.open_detect_candle_modal)
    tools_menu.add_command(label="Detectar Estrategias forex", command=app.action_handler.open_detect_forex_modal)
    tools_menu.add_separator()
    tools_menu.add_command(label="Iniciar Backtesting", command=app._run_perfect_backtesting)
    tools_menu.add_command(label="Finalizar backtesting", command=app._finalize_backtesting_action)
    app.analysis_tools_btn.state(["disabled"])

    # --- Menú de Opciones (Columna 1) ---
    app.options_btn = ttk.Menubutton(header, text="Opciones")
    app.options_btn.grid(row=0, column=1, padx=(10, 0))
    options_menu = tk.Menu(app.options_btn, tearoff=False)
    app.options_btn["menu"] = options_menu
    options_menu.add_checkbutton(label="Modo Debug", variable=app.debug_mode_var, command=app._toggle_debug_mode_action)
    options_menu.add_separator()
    options_menu.add_command(label="Guardar Gráfica", command=app.action_handler.save_chart_to_csv)
    options_menu.add_separator()
    options_menu.add_command(label="Configuración", command=app.action_handler.open_config_modal)
    options_menu.add_separator()
    options_menu.add_checkbutton(label="Mostrar Gráfica RSI", variable=app.show_rsi_var, command=app.action_handler.toggle_rsi_chart)
    options_menu.add_checkbutton(label="Mostrar Gráfica ATR", variable=app.show_atr_var, command=app.action_handler.toggle_atr_chart)
    options_menu.add_checkbutton(label="Mostrar Gráfica MACD", variable=app.show_macd_var, command=app.action_handler.toggle_macd_chart)
    options_menu.add_checkbutton(label="Mostrar Gráfica Momentum", variable=app.show_momentum_var, command=app.action_handler.toggle_momentum_chart)
    options_menu.add_separator()
    options_menu.add_command(label="Limpiar log", command=app.action_handler.clear_log)

    # --- Botón de Simulación (Columna 2) ---
    app.simulation_btn = ttk.Menubutton(header, text="Simulación")
    app.simulation_btn.grid(row=0, column=2, padx=(10, 0))
    simulation_menu = tk.Menu(app.simulation_btn, tearoff=False)
    app.simulation_btn["menu"] = simulation_menu
    app.simulation_menu = simulation_menu
    simulation_menu.add_command(label="Iniciar simulación", command=app._iniciar_simulacion_action)
    simulation_menu.add_command(label="Ver operaciones abiertas", command=app._ver_operaciones_abiertas_action, state="disabled")
    simulation_menu.add_command(label="Cerrar operaciones", command=app._cerrar_operaciones_action, state="disabled")
    simulation_menu.add_command(label="Detener simulación", command=app._detener_simulacion_action, state="disabled")
    simulation_menu.add_separator()
    simulation_menu.add_checkbutton(label="Modo agresivo", variable=app.modo_agresivo_activo, command=app._modo_agresivo_action)
    simulation_menu.entryconfig("Modo agresivo", state="disabled") # Deshabilitado por defecto
    simulation_menu.add_separator()
    simulation_menu.add_checkbutton(label="Pausar", command=app._detener_actualizacion_action)
    app.simulation_btn.state(["disabled"])

    # --- Labels for Simulation Results (Columna 3) ---
    results_frame = ttk.Frame(header, padding=(10, 0))
    results_frame.grid(row=0, column=3, sticky="ew", padx=(10, 0))

    results_frame.columnconfigure(1, minsize=80)
    results_frame.columnconfigure(3, minsize=80)
    results_frame.columnconfigure(5, minsize=80)

    ttk.Label(results_frame, text="Dinero inicial:").grid(row=0, column=0, sticky="w", padx=(0, 5))
    ttk.Label(results_frame, textvariable=app.initial_balance_var, foreground="black").grid(row=0, column=1, sticky="w")

    ttk.Label(results_frame, text="Equity:").grid(row=0, column=2, sticky="w", padx=(10, 5))
    ttk.Label(results_frame, textvariable=app.equity_var, foreground="#007ACC").grid(row=0, column=3, sticky="w")

    ttk.Label(results_frame, text="Beneficios:").grid(row=0, column=4, sticky="w", padx=(10, 5))
    ttk.Label(results_frame, textvariable=app.profit_var, foreground="green").grid(row=0, column=5, sticky="w")

    ttk.Label(results_frame, text="Margen:").grid(row=1, column=0, sticky="w", padx=(0, 5))
    ttk.Label(results_frame, textvariable=app.margin_var, foreground="#E59400").grid(row=1, column=1, sticky="w")

    ttk.Label(results_frame, text="Margen Libre:").grid(row=1, column=2, sticky="w", padx=(10, 5))
    ttk.Label(results_frame, textvariable=app.free_margin_var, foreground="#33A133").grid(row=1, column=3, sticky="w")

    ttk.Label(results_frame, text="Pérdidas:").grid(row=1, column=4, sticky="w", padx=(10, 5))
    ttk.Label(results_frame, textvariable=app.loss_var, foreground="red").grid(row=1, column=5, sticky="w")

    # Spacer para empujar los controles a la derecha (Columna 4)
    spacer = ttk.Frame(header)
    spacer.grid(row=0, column=4, sticky="ew")

    # El resto de los controles (desde la Columna 5 en adelante)
    ttk.Label(header, text="Símbolo:").grid(row=0, column=5, padx=(0, 6))
    app.symbol_cb = ttk.Combobox(header, textvariable=app.symbol_var, width=12, state="disabled")
    app.symbol_cb["values"] = ("EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "BTCUSD")
    app.symbol_cb.grid(row=0, column=6)
    app.symbol_cb.bind("<<ComboboxSelected>>", app._apply_chart_selection)

    ttk.Label(header, text="Timeframe:").grid(row=0, column=7, padx=(12, 6))
    app.timeframe_cb = ttk.Combobox(header, textvariable=app.timeframe_var, width=8, state="disabled")
    app.timeframe_cb["values"] = ("M1", "M5", "M15", "M30", "H1", "H4", "D1")
    app.timeframe_cb.grid(row=0, column=8)
    app.timeframe_cb.bind("<<ComboboxSelected>>", app._apply_chart_selection)

    app.start_btn = ttk.Button(header, text="Iniciar MT5", command=app._start_mt5_chart)
    app.start_btn.grid(row=0, column=9, padx=(12, 12))
    app.start_btn.state(["disabled"])

    app.status_label = ttk.Label(header, textvariable=app.status_var, foreground="black")
    app.status_label.grid(row=0, column=10, padx=(12, 12))

    conectar_btn = ttk.Button(header, text="Conectar", command=app.login_handler.open_login_modal)
    conectar_btn.grid(row=0, column=11, padx=(6, 12))

    # Configuración de las columnas del header
    header.columnconfigure(4, weight=1)  # El spacer (col 4) se expande

    return header
