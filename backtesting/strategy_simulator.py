import os
import sys
import pandas as pd
import numpy as np
import json

# --- Configuración de sys.path ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from candles.candle_list import CandlePatterns
from forex.forex_list import ForexStrategies

class StrategySimulator:
    """ 
    Clase encargada de ejecutar la simulación de estrategias de trading sobre datos históricos.
    """
    def __init__(self, simulation_config, candles_df):
        """
        Inicializa el simulador con la configuración proporcionada.
        """
        self.config = simulation_config
        self.candles_df = candles_df.copy() # Usar una copia para no modificar el original
        self.open_trades = []
        self.closed_trades = []
        self.balance = 10000 # Saldo inicial de ejemplo
        self.pip_value = 0.0001 # Para EURUSD, 1 pip = 0.0001. Debería ser dinámico por símbolo.

        # Mapeo de nombres de estrategias a funciones reales
        self.candle_strategy_functions = {name.replace('is_', ''): func for name, func in vars(CandlePatterns).items() if name.startswith('is_')}
        self.forex_strategy_functions = {name: func for name, func in vars(ForexStrategies).items() if name.startswith('strategy_')}

        print("StrategySimulator inicializado.")
        if self.candles_df is not None and not self.candles_df.empty:
            print(f"Datos de velas recibidos: {len(self.candles_df)} velas.")
            self.candles_df.columns = [col.lower() for col in self.candles_df.columns]
        else:
            print("Advertencia: No se recibieron datos de velas.")

    def _prepare_data(self):
        """Calcula todos los indicadores técnicos necesarios para las estrategias manualmente."""
        if self.candles_df is None or self.candles_df.empty:
            return
        
        print("Preparando datos y calculando indicadores técnicos manualmente...")
        df = self.candles_df

        # --- EMA ---
        df['ema_fast'] = df['close'].ewm(span=12, adjust=False).mean()
        df['ema_slow'] = df['close'].ewm(span=26, adjust=False).mean()
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()

        # --- RSI ---
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # --- MACD ---
        ema_fast = df['close'].ewm(span=12, adjust=False).mean()
        ema_slow = df['close'].ewm(span=26, adjust=False).mean()
        df['macd_line'] = ema_fast - ema_slow
        df['macd_signal'] = df['macd_line'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd_line'] - df['macd_signal']

        # --- Bollinger Bands ---
        sma20 = df['close'].rolling(window=20).mean()
        std20 = df['close'].rolling(window=20).std()
        df['bb_upper'] = sma20 + (std20 * 2)
        df['bb_lower'] = sma20 - (std20 * 2)

        # --- ATR ---
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = tr.ewm(alpha=1/14, adjust=False).mean()

        # --- Ichimoku Cloud ---
        high9 = df['high'].rolling(window=9).max()
        low9 = df['low'].rolling(window=9).min()
        df['tenkan_sen'] = (high9 + low9) / 2

        high26 = df['high'].rolling(window=26).max()
        low26 = df['low'].rolling(window=26).min()
        df['kijun_sen'] = (high26 + low26) / 2

        df['senkou_span_a'] = ((df['tenkan_sen'] + df['kijun_sen']) / 2).shift(26)

        high52 = df['high'].rolling(window=52).max()
        low52 = df['low'].rolling(window=52).min()
        df['senkou_span_b'] = ((high52 + low52) / 2).shift(26)

        # --- StochRSI (simplificado, ya que StochRSI completo es más complejo) ---
        rsi = df['rsi']
        rsi_min = rsi.rolling(window=14).min()
        rsi_max = rsi.rolling(window=14).max()
        stoch_rsi = (rsi - rsi_min) / (rsi_max - rsi_min)
        df['stochrsi_k'] = stoch_rsi.rolling(window=3).mean() * 100

        # Eliminar filas con NaN generadas por los indicadores
        self.candles_df.dropna(inplace=True)
        self.candles_df.reset_index(inplace=True, drop=True) # drop=True para no guardar el viejo índice
        print("Indicadores calculados. Velas disponibles para simulación:", len(self.candles_df))

    def run_simulation(self):
        """
        Ejecuta la simulación de backtesting iterando sobre cada vela.
        """
        print("\n--- Iniciando Simulación de Estrategia ---")
        if self.candles_df is None or self.candles_df.empty:
            print("Error: No se puede ejecutar la simulación sin datos de velas.")
            return

        self._prepare_data()
        
        selected_forex = self._get_selected_strategies('forex_strategies')
        selected_candles = self._get_selected_strategies('candle_strategies')
        
        candles_as_records = self.candles_df.to_dict('records')
        max_forex_slots = self.config.get('slots', {}).get('forex', 1)
        max_candle_slots = self.config.get('slots', {}).get('candle', 1)

        # Lista de estrategias conceptuales que no devuelven una señal simple y deben ser ignoradas
        conceptual_strategies_to_skip = [
            'strategy_conceptual_grid_trading',
            'strategy_conceptual_news_trading',
            'strategy_conceptual_hedging'
        ]

        # --- Bucle Principal de Simulación ---
        # Empezar desde el índice 1 para que siempre haya un dato anterior (i-1) disponible
        for i in range(1, len(self.candles_df)):
            current_candle = self.candles_df.iloc[i]
            current_price = current_candle['close']
            
            # Contar slots ocupados
            forex_slots_occupied = sum(1 for trade in self.open_trades if trade['source'] == 'forex')
            candle_slots_occupied = sum(1 for trade in self.open_trades if trade['source'] == 'candle')

            # --- 1. Evaluar Estrategias de Velas ---
            if candle_slots_occupied < max_candle_slots:
                for pattern_name, config in selected_candles:
                    clean_name = pattern_name.replace('is_', '')
                    if clean_name in self.candle_strategy_functions:
                        signal = self.candle_strategy_functions[clean_name](candles_as_records, i)
                        if signal in ['long', 'short']:
                            print(f"Señal de VELA '{clean_name}' ({signal}) en la vela {i} al precio {current_price:.5f}")
                            self._open_trade(i, current_price, signal, 'candle', clean_name, config)
                            break # Solo una operación por vela

            # --- 2. Evaluar Estrategias Forex ---
            if forex_slots_occupied < max_forex_slots:
                df_so_far = self.candles_df.iloc[:i+1]
                for strategy_name, config in selected_forex:
                    # Ignorar estrategias conceptuales que no son aplicables en este simulador
                    if strategy_name in conceptual_strategies_to_skip:
                        continue

                    if strategy_name in self.forex_strategy_functions:
                        signal = self.forex_strategy_functions[strategy_name](df_so_far)
                        if signal in ['long', 'short']:
                            print(f"Señal de FOREX '{strategy_name}' ({signal}) en la vela {i} al precio {current_price:.5f}")
                            self._open_trade(i, current_price, signal, 'forex', strategy_name, config)
                            break # Solo una operación por vela

            # --- 3. Gestionar Operaciones Abiertas ---
            self._manage_open_trades(i, current_candle)

        print("--- Simulación Finalizada ---")
        self._print_summary()

    def _get_selected_strategies(self, strategy_type):
        """
        Filtra y devuelve solo las estrategias que han sido seleccionadas en la configuración.
        """
        strategies = self.config.get(strategy_type, {})
        return [(name, config) for name, config in strategies.items() if config.get('selected')]

    def _open_trade(self, entry_index, entry_price, signal, source, strategy_name, config):
        """Abre una nueva operación y la añade a la lista de operaciones abiertas."""
        # Para EURUSD, 1 pip = 0.0001. Esto debería ser dinámico por símbolo.
        pip_value = self.pip_value
        
        if source == 'forex':
            sl_pips = config.get('stop_loss_pips', 20)
            rr_ratio = config.get('rr_ratio', 2.0)
            stop_loss_amount = sl_pips * pip_value
            take_profit_amount = stop_loss_amount * rr_ratio
        else: # 'candle'
            # Para velas, usamos un SL basado en ATR y un RR fijo
            atr = self.candles_df.iloc[entry_index]['atr']
            stop_loss_amount = atr * 1.5 # Ejemplo: SL a 1.5x ATR
            take_profit_amount = stop_loss_amount * 2.0 # Ejemplo: RR de 2.0

        if signal == 'long':
            stop_loss = entry_price - stop_loss_amount
            take_profit = entry_price + take_profit_amount
        else: # 'short'
            stop_loss = entry_price + stop_loss_amount
            take_profit = entry_price - take_profit_amount

        trade = {
            'entry_index': entry_index,
            'entry_price': entry_price,
            'type': signal,
            'status': 'open',
            'source': source,
            'strategy_name': strategy_name,
            'stop_loss': stop_loss,
            'take_profit': take_profit
        }
        self.open_trades.append(trade)
        print(f"    -> Trade ABIERTO: {signal} a {entry_price:.5f} | SL: {stop_loss:.5f}, TP: {take_profit:.5f}")

    def _manage_open_trades(self, current_index, current_candle):
        """Gestiona las operaciones abiertas, comprobando si se deben cerrar."""
        trades_to_close = []
        for trade in self.open_trades:
            exit_price = None
            close_reason = None

            if trade['type'] == 'long':
                # Comprobar si se alcanzó el Stop Loss
                if current_candle['low'] <= trade['stop_loss']:
                    exit_price = trade['stop_loss']
                    close_reason = 'Stop Loss'
                # Comprobar si se alcanzó el Take Profit
                elif current_candle['high'] >= trade['take_profit']:
                    exit_price = trade['take_profit']
                    close_reason = 'Take Profit'
            
            elif trade['type'] == 'short':
                # Comprobar si se alcanzó el Stop Loss
                if current_candle['high'] >= trade['stop_loss']:
                    exit_price = trade['stop_loss']
                    close_reason = 'Stop Loss'
                # Comprobar si se alcanzó el Take Profit
                elif current_candle['low'] <= trade['take_profit']:
                    exit_price = trade['take_profit']
                    close_reason = 'Take Profit'

            if exit_price is not None:
                trade['status'] = 'closed'
                trade['exit_index'] = current_index
                trade['exit_price'] = exit_price
                trade['close_reason'] = close_reason
                
                # Calcular P/L (en pips para simplificar)
                pnl_pips = (exit_price - trade['entry_price']) / self.pip_value if trade['type'] == 'long' else (trade['entry_price'] - exit_price) / self.pip_value
                trade['pnl_pips'] = pnl_pips
                self.balance += pnl_pips # Asumiendo 1 pip = 1 unidad de la moneda de la cuenta

                trades_to_close.append(trade)
                print(f"    -> Trade CERRADO: {trade['type']} de {trade['strategy_name']} por {close_reason}. P/L: {pnl_pips:.2f} pips. Balance: {self.balance:.2f}")

        # Mover las operaciones cerradas de la lista de abiertas a la de cerradas
        if trades_to_close:
            self.open_trades = [t for t in self.open_trades if t['status'] == 'open']
            self.closed_trades.extend(trades_to_close)

    def _print_summary(self):
        """Imprime un resumen de los resultados de la simulación."""
        print("\n--- Resumen de la Simulación ---")
        total_trades = len(self.closed_trades)
        if total_trades == 0:
            print("No se realizaron operaciones.")
            return

        wins = [t for t in self.closed_trades if t['pnl_pips'] > 0]
        losses = [t for t in self.closed_trades if t['pnl_pips'] <= 0]
        win_rate = (len(wins) / total_trades) * 100 if total_trades > 0 else 0
        
        total_pnl = sum(t['pnl_pips'] for t in self.closed_trades)
        avg_win = sum(t['pnl_pips'] for t in wins) / len(wins) if wins else 0
        avg_loss = sum(t['pnl_pips'] for t in losses) / len(losses) if losses else 0
        risk_reward_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')

        print(f"Operaciones Totales: {total_trades}")
        print(f"Ganadoras: {len(wins)}")
        print(f"Perdedoras: {len(losses)}")
        print(f"Tasa de Acierto: {win_rate:.2f}%")
        print(f"P/L Total (pips): {total_pnl:.2f}")
        print(f"Balance Final: {self.balance:.2f}")
        print(f"Ganancia Promedio (pips): {avg_win:.2f}")
        print(f"Pérdida Promedio (pips): {avg_loss:.2f}")
        print(f"Ratio Riesgo/Beneficio Real: {risk_reward_ratio:.2f}")

# Ejemplo de uso (para pruebas)
if __name__ == '__main__':
    # Crear un DataFrame de velas de ejemplo
    mock_dates = pd.to_datetime(pd.date_range(start='2023-01-01', periods=250, freq='H')) # Más datos para indicadores
    data = np.random.randn(250, 5).cumsum(axis=0) + 1.15
    mock_df = pd.DataFrame(data, columns=['open', 'high', 'low', 'close', 'volume'], index=mock_dates)
    mock_df['high'] = mock_df[['open', 'close']].max(axis=1) + np.random.uniform(0, 0.01, 250)
    mock_df['low'] = mock_df[['open', 'close']].min(axis=1) - np.random.uniform(0, 0.01, 250)
    mock_df['volume'] = np.random.randint(1000, 5000, 250)

    # Esta configuración de ejemplo simula lo que enviaría el modal
    mock_config = {
        "slots": {
            "forex": 1,
            "candle": 1
        },
        "candle_strategies": {
            "is_engulfing": {
                "selected": True,
                "strategy_mode": "Default"
            }
        },
        "forex_strategies": {
            "strategy_ma_crossover": {
                "selected": True,
                "percent_ratio": 1.0,
                "rr_ratio": 2.0,
                "stop_loss_pips": 20.0
            }
        }
    }

    simulator = StrategySimulator(mock_config, mock_df)
    simulator.run_simulation()