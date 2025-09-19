

1. quiero que en el modal strategy_simulator_modal.py cuando se pulse iniciar coga todas las estrategias seleccionadas, forex y candle con sus respectivas configuraciones, y sobre el inicio de la grafica hasta el fin ....


2. quiero que en el modal strategy_simulator_modal.py una fila mas arriba de los botones canelar e iniciar agregues lo siguiente:
- En una linea pongas dos labels slots forex y slots candles y un texbox numerico para cada uno.
- Si en slot forex pongo 0 no se ejecutaran las estrategias forex seleccionadas con sus configuraciones sobre la grafica.
- Si en slot candles pongo 0 no se ejecutaran las estrategias candles seleccionadas con sus configuraciones sobre la grafica.


quiero que a la derecha de herramientas agregues un desplegable que tenga de nombre simulación y tenga dos opciones: 
    - iniciar simulación
    - abrir operación manual
    - modificar estrategias
    - cancelar simulación


    # simulation_menu = tk.Menu(self.menu_bar, tearoff=0)
        # self.menu_bar.add_cascade(label="Simulación", menu=simulation_menu, state="disabled")
        # simulation_menu.add_command(label="Iniciar simulación", command=self._iniciar_simulacion_action)
        # simulation_menu.add_command(label="Abrir operación manual", command=self._abrir_operacion_manual_action)
        # simulation_menu.add_command(label="Modificar estrategias", command=self._modificar_estrategias_action)
        # simulation_menu.add_separator()
        # simulation_menu.add_command(label="Cancelar simulación", command=self._cancelar_simulacion_action)