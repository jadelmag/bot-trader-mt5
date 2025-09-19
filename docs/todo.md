


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
