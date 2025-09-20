import os
import sys
import pandas as pd
import numpy as np
import json
import logging

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
    def __init__(self, simulation_config, candles_df, logger, initial_capital=1000.0):
        """
        Inicializa el simulador con la configuración proporcionada.
        """
        self.config = simulation_config
        self.candles_df = candles_df.copy() # Usar una copia para no modificar el original
        self.logger = logger
        self.initial_capital = initial_capital
        self.current_balance = initial_capital
        self.open_trades = []
        self.closed_trades = []
        
        # --- Constantes de Trading --- 
        self.pip_value = 0.0001 # Valor de 1 pip para un par como EUR/USD
        self.pip_value_per_lot = 10 # Valor monetario de 1 pip por lote estándar (ej: $10)

        # Mapeo de nombres de estrategias a funciones reales
        self.candle_strategy_functions = {name.replace('is_', ''): func for name, func in vars(CandlePatterns).items() if name.startswith('is_')}
        self.forex_strategy_functions = {name: func for name, func in vars(ForexStrategies).items() if name.startswith('strategy_')}

        self.logger.log("StrategySimulator inicializado.")
        if self.candles_df is not None and not self.candles_df.empty:
            self.logger.log(f"Datos de velas recibidos: {len(self.candles_df)} velas.")
            self.candles_df.columns = [col.lower() for col in self.candles_df.columns]
        else:
            self.logger.error("Advertencia: No se recibieron datos de velas.")

    def _prepare_data(self):
        """Calcula todos los indicadores técnicos necesarios para las estrategias manualmente."""
        if self.candles_df is None or self.candles_df.empty:
            return
        
        self.logger.log("Preparando datos y calculando indicadores técnicos manualmente...")
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
        self.logger.log(f"Indicadores calculados. Velas disponibles para simulación: {len(self.candles_df)}")

    def _calculate_lot_size(self, stop_loss_pips, risk_percent):
        """Calcula el tamaño del lote basado en el capital actual, el riesgo y el SL."""
        if stop_loss_pips <= 0:
            return 0.01 # Retornar un lote mínimo si el SL es inválido

        capital_at_risk = self.current_balance * (risk_percent / 100.0)
        sl_value_per_lot = stop_loss_pips * self.pip_value_per_lot
        
        if sl_value_per_lot <= 0:
            return 0.01 # Evitar división por cero

        lot_size = capital_at_risk / sl_value_per_lot
        
        # Redondear al tamaño de lote más cercano (ej. 0.01)
        return max(0.01, round(lot_size, 2))

    def run_simulation(self):
        """
        Ejecuta la simulación de backtesting iterando sobre cada vela.
        """
        self.logger.log("\n--- Iniciando Simulación de Estrategia ---")
        if self.candles_df is None or self.candles_df.empty:
            self.logger.error("Error: No se puede ejecutar la simulación sin datos de velas.")
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
                            self.logger.log(f"Señal de VELA '{clean_name}' ({signal}) en la vela {i} al precio {current_price:.5f}")
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
                            self.logger.log(f"Señal de FOREX '{strategy_name}' ({signal}) en la vela {i} al precio {current_price:.5f}")
                            self._open_trade(i, current_price, signal, 'forex', strategy_name, config)
                            break # Solo una operación por vela

            # --- 3. Gestionar Operaciones Abiertas ---
            self._manage_open_trades(i, current_candle)

        self.logger.success("--- Simulación Finalizada ---")
        self._print_summary()

    def _get_selected_strategies(self, strategy_type):
        """
        Filtra y devuelve solo las estrategias que han sido seleccionadas en la configuración.
        """
        strategies = self.config.get(strategy_type, {})
        return [(name, config) for name, config in strategies.items() if config.get('selected')]

    def _open_trade(self, entry_index, entry_price, signal, source, strategy_name, config):
        """Abre una nueva operación y la añade a la lista de operaciones abiertas."""
        stop_loss_pips = 0
        risk_percent = 1.0 # Riesgo por defecto del 1%

        if source == 'forex':
            stop_loss_pips = config.get('stop_loss_pips', 20)
            rr_ratio = config.get('rr_ratio', 2.0)
            risk_percent = config.get('percent_ratio', 1.0)
        else: # 'candle'
            # Extraer la configuración detallada del patrón
            pattern_config = config.get('config', {})
            use_sl = pattern_config.get('use_stop_loss', True)

            if not use_sl:
                self.logger.log(f"    -> Trade RECHAZADO: El Stop Loss está desactivado para '{strategy_name}'.")
                return

            atr = self.candles_df.iloc[entry_index]['atr']
            atr_sl_multiplier = pattern_config.get('atr_sl_multiplier', 1.5)
            atr_tp_multiplier = pattern_config.get('atr_tp_multiplier', 2.0)
            
            # Convertir el SL basado en ATR a pips
            stop_loss_pips = (atr * atr_sl_multiplier) / self.pip_value
            rr_ratio = atr_tp_multiplier / atr_sl_multiplier if atr_sl_multiplier > 0 else 0

        if stop_loss_pips <= 0:
            self.logger.error(f"    -> Trade RECHAZADO: Stop loss inválido ({stop_loss_pips} pips) para {strategy_name}")
            return

        lot_size = self._calculate_lot_size(stop_loss_pips, risk_percent)
        if self.current_balance < (lot_size * stop_loss_pips * self.pip_value_per_lot):
            self.logger.log(f"    -> Trade RECHAZADO: Balance insuficiente para cubrir el riesgo.")
            return

        stop_loss_amount = stop_loss_pips * self.pip_value
        take_profit_amount = (stop_loss_pips * rr_ratio) * self.pip_value

        if signal == 'long':
            stop_loss = entry_price - stop_loss_amount
            take_profit = entry_price + take_profit_amount
        else: # 'short'
            stop_loss = entry_price + stop_loss_amount
            take_profit = entry_price - take_profit_amount

        risked_amount = lot_size * stop_loss_pips * self.pip_value_per_lot

        trade = {
            'entry_index': entry_index,
            'entry_price': entry_price,
            'type': signal,
            'status': 'open',
            'source': source,
            'strategy_name': strategy_name,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'lot_size': lot_size,
            'risked_amount': risked_amount
        }
        self.open_trades.append(trade)
        self.logger.log(f"    -> Trade ABIERTO: {signal} a {entry_price:.5f} | Lote: {lot_size:.2f} | Riesgo: ${risked_amount:.2f}")

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
                
                # Calcular P/L en pips y en dinero
                pnl_pips = (exit_price - trade['entry_price']) / self.pip_value if trade['type'] == 'long' else (trade['entry_price'] - exit_price) / self.pip_value
                pnl_money = pnl_pips * trade['lot_size'] * self.pip_value_per_lot
                
                trade['pnl_pips'] = pnl_pips
                trade['pnl_money'] = pnl_money
                self.current_balance += pnl_money

                trades_to_close.append(trade)
                log_msg = f"    -> Trade CERRADO: {trade['type']} de {trade['strategy_name']} por {close_reason}. P/L: ${pnl_money:.2f} ({pnl_pips:.2f} pips). Balance: ${self.current_balance:.2f}"
                if pnl_money > 0:
                    self.logger.success(log_msg)
                else:
                    self.logger.error(log_msg)

        # Mover las operaciones cerradas de la lista de abiertas a la de cerradas
        if trades_to_close:
            self.open_trades = [t for t in self.open_trades if t['status'] == 'open']
            self.closed_trades.extend(trades_to_close)

    def _print_summary(self):
        """Imprime un resumen de los resultados de la simulación."""
        self.logger.log("\n" + "="*25 + " Resumen de la Simulación " + "="*25)
        total_trades = len(self.closed_trades)
        if total_trades == 0:
            self.logger.log("No se realizaron operaciones.")
            return

        wins = [t for t in self.closed_trades if t['pnl_money'] > 0]
        losses = [t for t in self.closed_trades if t['pnl_money'] <= 0]
        win_rate = (len(wins) / total_trades) * 100 if total_trades > 0 else 0
        
        total_pnl_money = sum(t['pnl_money'] for t in self.closed_trades)
        total_profits = sum(t['pnl_money'] for t in wins)
        total_losses = sum(t['pnl_money'] for t in losses)
        total_risked = sum(t['risked_amount'] for t in self.closed_trades)

        avg_win = total_profits / len(wins) if wins else 0
        avg_loss = total_losses / len(losses) if losses else 0
        risk_reward_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')

        self.logger.log(f"Capital Inicial: ${self.initial_capital:.2f}")
        self.logger.log(f"Capital Final: ${self.current_balance:.2f}")
        self.logger.log(f"Beneficio Neto: ${total_pnl_money:.2f}")
        self.logger.log(f"Total Ganancias: ${total_profits:.2f}")
        self.logger.log(f"Total Pérdidas: ${total_losses:.2f}")
        self.logger.log(f"Total Arriesgado: ${total_risked:.2f}")
        self.logger.log("-"*35)
        self.logger.log(f"Operaciones Totales: {total_trades}")
        self.logger.log(f"Ganadoras: {len(wins)}")
        self.logger.log(f"Perdedoras: {len(losses)}")
        self.logger.log(f"Tasa de Acierto: {win_rate:.2f}%")
        self.logger.log(f"Ganancia Promedio: ${avg_win:.2f}")
        self.logger.log(f"Pérdida Promedio: ${avg_loss:.2f}")
        self.logger.log(f"Ratio Riesgo/Beneficio Real: {risk_reward_ratio:.2f}")
        self.logger.log("="*75 + "\n")