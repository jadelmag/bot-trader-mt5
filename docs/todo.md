

1. quiero que en el modal strategy_simulator_modal.py cuando se pulse iniciar coga todas las estrategias seleccionadas, forex y candle con sus respectivas configuraciones, y abra operaciones short y long tanto de forex como de candle, cuando crea conveniente para sacar el mayor beneficio posible y sobre todo evitar el mayor numero de perdidas, sobre la grafica desde su inicio hasta su fin. Y se realizara en el archivo strategy_simulator.py


  # --- Botón de Simulación (Columna 1) ---
        self.simulation_btn = ttk.Menubutton(header, text="Simulación")
        self.simulation_btn.grid(row=0, column=1, padx=(10, 0)) # 10px de separación a la izquierda
        simulation_menu = tk.Menu(self.simulation_btn, tearoff=False)
        self.simulation_btn["menu"] = simulation_menu
        simulation_menu.add_command(label="Iniciar simulación", command=self._iniciar_simulacion_action)
        simulation_menu.add_command(label="Abrir operación manual", command=self._abrir_operacion_manual_action)
        simulation_menu.add_command(label="Modificar estrategias", command=self._modificar_estrategias_action)
        simulation_menu.add_separator()
        simulation_menu.add_command(label="Cancelar simulación", command=self._cancelar_simulacion_action)
        self.simulation_btn.state(["disabled"])

            def _iniciar_simulacion_action(self):
        """Lanza la simulación."""
        self._log_info("TODO: Iniciar simulación")

    def _abrir_operacion_manual_action(self):
        """Abre una operación manual."""
        self._log_info("TODO: Abriendo operación manual")

    def _modificar_estrategias_action(self):
        """Modifica las estrategias."""
        self._log_info("TODO: Modificar estrategias")

    def _cancelar_simulacion_action(self):
        """Cancela la simulación."""
        self._log_info("TODO: Cancelar simulación")
