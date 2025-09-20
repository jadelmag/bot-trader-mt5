
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
