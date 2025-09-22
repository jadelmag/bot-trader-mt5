import time

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

class CustomStrategies:
    """
    Clase que contiene estrategias personalizadas
    """

    @staticmethod
    def strategy_pico_y_pala(df):
        """
        Estrategia de pico y pala basada en velas
        """
        body_size = abs(df['close'] - df['open'])
        range_size = df['high'] - df['low']

        # Evitamos división por cero
        if range_size == 0:
            return None

        # Si el cuerpo es más del 60% del rango total → señal fuerte
        if body_size / range_size > 0.6:
            if df['close'] > df['open']:
                return "long"
            elif df['open'] > df['close']:
                return "short"
        return None

    @staticmethod
    def run_pico_y_pala(simulation_instance, symbol: str, volume: float, logger=None):
        """
        Estrategia de scalping de alta frecuencia "Pico y Pala".
        Recibe la instancia de la simulación activa para interactuar con ella.
        """
        if not mt5:
            if logger:
                logger.error("[PICO Y PALA] MT5 no está disponible.")
            return

        # --- Fase 1: Determinar la dirección (10 segundos) ---
        if logger: logger.log("[PICO Y PALA] Fase 1: Analizando momentum durante 10 segundos...")
        
        ups = 0
        downs = 0
        last_price = 0
        start_time = time.time()

        while time.time() - start_time < 10:
            tick = mt5.symbol_info_tick(symbol)
            if tick and tick.last != last_price:
                if last_price != 0:
                    if tick.last > last_price:
                        ups += 1
                    else:
                        downs += 1
                last_price = tick.last
            time.sleep(0.1) # Pequeña pausa para no saturar la CPU

        direction = 'long' if ups > downs else 'short'
        if logger: logger.log(f"[PICO Y PALA] Dirección determinada: {direction.upper()} (Ups: {ups}, Downs: {downs})")

        # --- Fase 2: Abrir y gestionar la operación (20 segundos) ---
        # Ya no se crea una instancia de Simulation, se usa la que se pasa como argumento
        
        # Abrir la operación sin TP y con un SL de emergencia amplio
        result = simulation_instance.open_trade(trade_type=direction, symbol=symbol, volume=volume, sl_pips=50, tp_pips=0)
        if not result or result.retcode != mt5.TRADE_RETCODE_DONE:
            if logger: logger.error("[PICO Y PALA] No se pudo abrir la operación.")
            return

        position_ticket = result.order
        if logger: logger.log(f"[PICO Y PALA] Fase 2: Operación {direction.upper()} abierta (Ticket: {position_ticket}). Gestionando durante 20 segundos...")

        start_time_manage = time.time()
        peak_price = 0
        trough_price = float('inf')
        
        while time.time() - start_time_manage < 20:
            tick = mt5.symbol_info_tick(symbol)
            if not tick: 
                time.sleep(0.1)
                continue

            current_price = tick.last
            
            if direction == 'long':
                # Actualizar el precio máximo alcanzado
                if current_price > peak_price: peak_price = current_price
                # Si el precio, tras caer, vuelve al pico, cerramos (objetivo principal)
                if current_price < peak_price and current_price >= peak_price * 0.9999: # Cerca del pico
                    if logger: logger.log(f"[PICO Y PALA] Objetivo LONG alcanzado. Cerrando cerca del pico {peak_price}.")
                    simulation_instance.close_trade(position_ticket, volume, 'long')
                    return
            
            elif direction == 'short':
                # Actualizar el precio mínimo alcanzado
                if current_price < trough_price: trough_price = current_price
                # Si el precio, tras subir, vuelve al mínimo, cerramos (objetivo principal)
                if current_price > trough_price and current_price <= trough_price * 1.0001: # Cerca del mínimo
                    if logger: logger.log(f"[PICO Y PALA] Objetivo SHORT alcanzado. Cerrando cerca del mínimo {trough_price}.")
                    simulation_instance.close_trade(position_ticket, volume, 'short')
                    return

            time.sleep(0.1)

        # Si el tiempo se agota, cerramos la operación forzosamente
        if logger: logger.log("[PICO Y PALA] Tiempo de gestión agotado. Forzando cierre.")
        simulation_instance.close_trade(position_ticket, volume, direction)
