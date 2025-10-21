    def calculate_volume(self, risk_multiplier=1.0):
        """Calcula el volumen de la operación basado en el riesgo porcentual del equity."""
        if not mt5 or not mt5.terminal_info():
            return 0.0

        try:
            account_info = mt5.account_info()
            symbol_info = mt5.symbol_info(self.simulation.symbol)

            if not account_info or not symbol_info:
                self._log("[RISK-ERROR] No se pudo obtener información de la cuenta o del símbolo.", 'error')
                return 0.0

            # PROBLEMA:
            # No calcula el volumen basado en el SL como debería
            # Usa directamente el risk_per_trade_percent como volumen
            # Con risk_per_trade_percent = 100.0 en config.json, está arriesgando 100 lotes por operación
            
            risk_per_trade_percent = float(self.simulation.general_config.get('risk_per_trade_percent', 1.0))
            volume = risk_per_trade_percent * (risk_multiplier / 100.0)

            # Ajustar si está fuera de rango
            if volume < symbol_info.volume_min:
                self._log(f"[RISK-WARN] Volumen menor que el mínimo ({symbol_info.volume_min}). Ajustado.", 'warn')
                volume = symbol_info.volume_min
            elif volume > symbol_info.volume_max:
                self._log(f"[RISK-WARN] Volumen mayor que el máximo ({symbol_info.volume_max}). Ajustado.", 'warn')
                volume = symbol_info.volume_max

            # Asegurar múltiplo del step
            step = symbol_info.volume_step
            if step > 0 and (volume % step) != 0:
                original_volume = volume
                volume = math.floor(volume / step) * step
                self._log(f"[RISK-WARN] Volumen ajustado: {original_volume:.6f} → {volume:.6f} (step={step})", 'warn')

            return round(volume, 6)

        except Exception as e:
            self._log(f"[RISK-ERROR] Error al calcular el volumen: {str(e)}", 'error')
            return 0.0