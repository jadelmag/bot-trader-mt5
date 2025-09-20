import uuid
import pandas as pd
import sys
import os
import json

# --- MT5 Integration ---
try:
    import MetaTrader5 as mt5
except ImportError:
    print("MetaTrader5 no está instalado. Las operaciones no se ejecutarán.")
    mt5 = None

# --- Path Setup ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# --- Config Path ---
CONFIG_PATH = os.path.join(PROJECT_ROOT, "strategies", "config.json")

from backtesting.detect_candles import CandleDetector
from backtesting.apply_strategies import StrategyAnalyzer


class Simulation:
    """
    Manages the state of a trading simulation, including account metrics, open trades, and P/L.
    """
    def __init__(self, initial_balance: float, symbol: str, timeframe: str, strategies_config: dict = None, logger=None):
        """
        Initializes the simulation with a starting balance.

        Args:
            initial_balance (float): The starting capital for the simulation.
            symbol (str): The financial instrument being traded.
            timeframe (str): The timeframe for candles (e.g., 'M1', 'M5').
            strategies_config (dict, optional): Configuration for candle and forex strategies. Defaults to None.
            logger (BodyLogger, optional): Instance of the logger for UI feedback. Defaults to None.
        """
        self.balance = initial_balance
        self.equity = initial_balance
        self.margin = 0.0
        self.free_margin = initial_balance
        self.total_profit = 0.0
        self.total_loss = 0.0
        self.symbol = symbol
        self.timeframe = timeframe
        self.timeframe_delta = self._get_timeframe_delta(timeframe)
        
        self.open_trades = []
        self.trades_in_current_candle = 0

        # --- Logger and Configs ---
        self.logger = logger
        self.strategies_config = strategies_config if strategies_config is not None else {}
        self.general_config = self._load_general_config()

        # --- Candle and Market Analysis Data ---
        self.candles_df = pd.DataFrame(columns=['time', 'open', 'high', 'low', 'close'])
        self.current_candle = None
        self.ma_fast = None
        self.ma_slow = None

    def _get_timeframe_delta(self, timeframe_str):
        """Converts a timeframe string to a pandas Timedelta."""
        mapping = {
            "M1": pd.Timedelta(minutes=1),
            "M5": pd.Timedelta(minutes=5),
            "M15": pd.Timedelta(minutes=15),
            "M30": pd.Timedelta(minutes=30),
            "H1": pd.Timedelta(hours=1),
            "H4": pd.Timedelta(hours=4),
            "D1": pd.Timedelta(days=1),
        }
        return mapping.get(timeframe_str.upper())

    def _log(self, message, level='info'):
        """Helper para registrar mensajes en la UI si el logger está disponible."""
        if not self.logger:
            print(message) # Fallback a la consola
            return
        
        log_methods = {
            'info': self.logger.log,
            'success': self.logger.success,
            'error': self.logger.error,
            'warn': self.logger.warn
        }
        log_methods.get(level, self.logger.log)(message)

    def _load_general_config(self):
        """Carga la configuración general desde config.json."""
        if not os.path.exists(CONFIG_PATH):
            return {}
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, TypeError):
            self._log("[SIM-ERROR] El archivo de configuración general 'config.json' está corrupto.", 'error')
            return {}

    def on_tick(self, timestamp, price):
        """
        Processes a new market tick, aggregating it into candles.
        """
        if not self.timeframe_delta:
            return

        # Align timestamp to the start of the candle's timeframe interval
        candle_start_time = timestamp.floor(self.timeframe_delta)

        # --- New Candle Detection ---
        if self.current_candle is None or candle_start_time > self.current_candle['time']:
            # Finalize the previous candle if it exists
            if self.current_candle is not None:
                # --- NEW CANDLE FORMED --- 
                self.trades_in_current_candle = 0 # Reset counter for the new candle
                self._log(f"[SIM] Nueva vela {self.timeframe} formada a las {candle_start_time}. Contador de trades reseteado.")

                new_row = pd.DataFrame([self.current_candle])
                self.candles_df = pd.concat([self.candles_df, new_row], ignore_index=True)
                # A new candle has been confirmed, run analysis
                self._analyze_market_and_execute_strategy()

            # Start a new candle
            self.current_candle = {
                'time': candle_start_time,
                'open': price,
                'high': price,
                'low': price,
                'close': price
            }
        else:
            # Update the current candle
            self.current_candle['high'] = max(self.current_candle['high'], price)
            self.current_candle['low'] = min(self.current_candle['low'], price)
            self.current_candle['close'] = price

        # Update floating P/L for open trades based on the latest price
        self.update_trades({self.symbol: price})

    def _analyze_market_and_execute_strategy(self):
        """
        Analyzes the market on each new completed candle to make trading decisions.
        """
        if self.candles_df.empty or not self.strategies_config:
            return

        # --- 0. Comprobación de Límite de Equity (Protección de Capital) ---
        equity_limit = self.general_config.get('money_limit', 0.0)
        if equity_limit > 0:
            account_info = mt5.account_info()
            if account_info and account_info.equity < equity_limit:
                self._log(f"[SIM-PROTECTION] Equity ({account_info.equity:.2f}) está por debajo del límite ({equity_limit:.2f}). No se abrirán nuevas operaciones.", 'warn')
                return

        # --- 1. Comprobación de Máx. de Operaciones por Vela ---
        max_orders_per_candle = self.general_config.get('max_orders_per_candle', 1)
        if self.trades_in_current_candle >= max_orders_per_candle:
            return # No abrir más operaciones en esta vela

        # Ensure DataFrame has correct column names for analyzers
        analysis_df = self.candles_df.rename(columns={
            'open': 'open', 'high': 'high', 'low': 'low', 'close': 'close'
        })

        # --- 2. Obtener señales de mercado ---
        ma_signal = self._get_ma_signal(analysis_df)
        candle_signal = self._get_candle_signal(analysis_df)

        # --- 3. Lógica de Cierre de Operaciones ---
        self._check_for_closing_signals(ma_signal, candle_signal)

        # --- 4. Lógica de Apertura de Operaciones ---
        open_positions = mt5.positions_get(symbol=self.symbol)
        if open_positions is None:
            open_positions = []
        
        active_slots = len(open_positions)
        max_slots = self.strategies_config.get('slots', {}).get('forex', 1)

        if active_slots >= max_slots:
            return

        forex_params = self._get_active_forex_params()
        current_price = self.candles_df.iloc[-1]['close']

        sl_pips = forex_params.get('stop_loss_pips', 20.0)
        volume = self._calculate_volume(sl_pips)

        if volume <= 0:
            return

        if ma_signal == 'long' and candle_signal == 'long':
            self._log(f"[SIM] Open LONG signal confirmed at {current_price}")
            self.open_trade(
                trade_type='long', 
                symbol=self.symbol, 
                volume=volume,
                sl_pips=sl_pips,
                tp_pips=sl_pips * forex_params.get('rr_ratio', 2.0)
            )
        
        elif ma_signal == 'short' and candle_signal == 'short':
            self._log(f"[SIM] Open SHORT signal confirmed at {current_price}")
            self.open_trade(
                trade_type='short', 
                symbol=self.symbol, 
                volume=volume,
                sl_pips=sl_pips,
                tp_pips=sl_pips * forex_params.get('rr_ratio', 2.0)
            )

    def _get_ma_signal(self, df):
        """Calculates moving averages and returns a 'long', 'short', or 'neutral' signal."""
        if len(df) < 50: # Need enough data for slow MA
            return 'neutral'
        
        fast_ma = df['close'].rolling(window=10).mean().iloc[-1]
        slow_ma = df['close'].rolling(window=50).mean().iloc[-1]
        
        if fast_ma > slow_ma:
            return 'long'
        elif fast_ma < slow_ma:
            return 'short'
        return 'neutral'

    def _get_candle_signal(self, df):
        """Analyzes the last candle for patterns selected in the strategy config."""
        candle_strategies = self.strategies_config.get('candle_strategies', {})
        if not candle_strategies:
            return 'neutral'

        selected_patterns = [
            name.replace('is_', '') 
            for name, config in candle_strategies.items() 
            if config.get('selected')
        ]

        if not selected_patterns:
            return 'neutral'

        detector = CandleDetector(df)
        last_candle_index = len(df) - 1
        
        for pattern_name in selected_patterns:
            detection_func = detector.pattern_methods.get(f'is_{pattern_name}')
            if detection_func:
                signal = detection_func(df.to_dict('records'), last_candle_index)
                if signal in ['long', 'short']:
                    self._log(f"[SIM] Candle signal detected: {pattern_name} -> {signal}")
                    return signal # Return the first signal found
        return 'neutral'

    def _get_active_forex_params(self):
        """Encuentra la primera estrategia de forex activa y devuelve sus parámetros."""
        forex_strategies = self.strategies_config.get('forex_strategies', {})
        for name, config in forex_strategies.items():
            if config.get('selected'):
                return {
                    'percent_ratio': config.get('percent_ratio', 1.0),
                    'rr_ratio': config.get('rr_ratio', 2.0),
                    'stop_loss_pips': config.get('stop_loss_pips', 20.0)
                }
        return {'percent_ratio': 1.0, 'rr_ratio': 2.0, 'stop_loss_pips': 20.0}

    def _calculate_volume(self, sl_pips: float):
        """Calcula el volumen de la operación basado en el riesgo porcentual del equity."""
        if not mt5 or not mt5.terminal_info() or sl_pips <= 0:
            return 0.0

        try:
            account_info = mt5.account_info()
            symbol_info = mt5.symbol_info(self.symbol)

            if not account_info or not symbol_info:
                self._log("[SIM-ERROR] No se pudo obtener información de la cuenta o del símbolo para calcular el volumen.", 'error')
                return 0.0

            equity = account_info.equity
            risk_percent = self.general_config.get('risk_per_trade_percent', 1.0)
            
            money_to_risk = equity * (risk_percent / 100.0)

            sl_in_points = sl_pips * (10 if symbol_info.digits in [3, 5] else 1)
            loss_per_lot = sl_in_points * symbol_info.trade_tick_value

            if loss_per_lot <= 0:
                return 0.0

            volume = money_to_risk / loss_per_lot

            volume_step = symbol_info.volume_step
            volume = round(volume / volume_step) * volume_step

            if volume < symbol_info.volume_min:
                self._log(f"[SIM-WARN] Volumen calculado ({volume:.2f}) es menor que el mínimo ({symbol_info.volume_min}). No se abrirá operación.", 'warn')
                return 0.0
            if volume > symbol_info.volume_max:
                volume = symbol_info.volume_max
                self._log(f"[SIM-WARN] Volumen calculado excede el máximo. Se ajustará a {symbol_info.volume_max}.", 'warn')

            return volume

        except Exception as e:
            self._log(f"[SIM-ERROR] Error al calcular el volumen: {e}", 'error')
            return 0.0

    def _check_for_closing_signals(self, ma_signal, candle_signal):
        """Itera sobre las posiciones abiertas y las cierra si hay una señal contraria fuerte."""
        if not mt5 or not mt5.terminal_info():
            return

        open_positions = mt5.positions_get(symbol=self.symbol)
        if open_positions is None or len(open_positions) == 0:
            return

        for position in open_positions:
            if position.type == mt5.POSITION_TYPE_BUY and ma_signal == 'short' and candle_signal == 'short':
                self._log(f"[SIM] Señal contraria detectada. Cerrando posición LONG #{position.ticket}.", 'warn')
                self.close_trade(position.ticket, position.volume, 'long')

            elif position.type == mt5.POSITION_TYPE_SELL and ma_signal == 'long' and candle_signal == 'long':
                self._log(f"[SIM] Señal contraria detectada. Cerrando posición SHORT #{position.ticket}.", 'warn')
                self.close_trade(position.ticket, position.volume, 'short')

    def open_trade(self, trade_type: str, symbol: str, volume: float, sl_pips: float = 0, tp_pips: float = 0):
        """
        Opens a new trade by sending an order to MetaTrader 5.
        """
        if not mt5 or not mt5.terminal_info():
            self._log("[SIM-ERROR] MT5 no está conectado. No se puede abrir la operación.", 'error')
            return None

        order_type = mt5.ORDER_TYPE_BUY if trade_type == 'long' else mt5.ORDER_TYPE_SELL
        price = mt5.symbol_info_tick(symbol).ask if trade_type == 'long' else mt5.symbol_info_tick(symbol).bid
        point = mt5.symbol_info(symbol).point

        sl = 0.0
        tp = 0.0

        if trade_type == 'long':
            if sl_pips > 0: sl = price - sl_pips * point
            if tp_pips > 0: tp = price + tp_pips * point
        else: # short
            if sl_pips > 0: sl = price + sl_pips * point
            if tp_pips > 0: tp = price - tp_pips * point

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": order_type,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": 20,
            "magic": 234000,
            "comment": "Sent by Bot-Trader-MT5",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            self._log(f"[SIM-ERROR] order_send falló, retcode={result.retcode}", 'error')
        else:
            money_risked = self._calculate_money_risk(volume, sl_pips)
            self._log(f"[SIM] Operación {trade_type.upper()} abierta ({volume:.2f} lots). Riesgo: ~{money_risked:.2f} $. Ticket: {result.order}", 'success')
            self.trades_in_current_candle += 1

        return result

    def update_trades(self, current_prices: dict):
        """
        Updates the floating profit/loss for all open trades based on current market prices.
        """
        total_floating_pl = 0.0
        for trade in self.open_trades:
            if trade['symbol'] in current_prices:
                current_price = current_prices[trade['symbol']]
                if trade['type'] == 'long':
                    trade['floating_pl'] = (current_price - trade['open_price']) * trade['volume']
                else: # short
                    trade['floating_pl'] = (trade['open_price'] - current_price) * trade['volume']
                
                total_floating_pl += trade['floating_pl']

        self.equity = self.balance + total_floating_pl
        self.free_margin = self.equity - self.margin

    def close_trade(self, position_ticket: int, volume: float, trade_type: str):
        """
        Closes an open position in MetaTrader 5.
        """
        if not mt5 or not mt5.terminal_info():
            self._log("[SIM-ERROR] MT5 no está conectado. No se puede cerrar la operación.", 'error')
            return None

        position_info = mt5.positions_get(ticket=position_ticket)
        if not position_info:
            self._log(f"[SIM-ERROR] No se encontró la posición con ticket {position_ticket}.", 'error')
            return None
        position_info = position_info[0]

        symbol = position_info.symbol
        order_type = mt5.ORDER_TYPE_SELL if trade_type == 'long' else mt5.ORDER_TYPE_BUY
        price = mt5.symbol_info_tick(symbol).bid if trade_type == 'long' else mt5.symbol_info_tick(symbol).ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": order_type,
            "position": position_ticket,
            "price": price,
            "deviation": 20,
            "magic": 234000,
            "comment": "Closed by Bot-Trader-MT5",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            self._log(f"[SIM-ERROR] Cierre de orden falló, retcode={result.retcode}", 'error')
        else:
            profit = result.profit
            if profit >= 0:
                self._log(f"[SIM] Posición {position_ticket} cerrada. Beneficio: {profit:.2f} $", 'success')
            else:
                self._log(f"[SIM] Posición {position_ticket} cerrada. Pérdida: {profit:.2f} $", 'error')

        return result

    def _calculate_money_risk(self, volume, sl_pips):
        """Calcula el riesgo monetario aproximado de una operación."""
        try:
            symbol_info = mt5.symbol_info(self.symbol)
            if not symbol_info:
                return 0.0
            
            sl_in_points = sl_pips * (10 if symbol_info.digits in [3, 5] else 1)
            loss_per_lot = sl_in_points * symbol_info.trade_tick_value
            return loss_per_lot * volume
        except Exception:
            return 0.0

    def get_account_summary(self):
        """
        Returns a summary of the current account status from MetaTrader 5.
        """
        if not mt5 or not mt5.terminal_info():
            return {
                "balance": self.balance,
                "equity": self.equity,
                "margin": self.margin,
                "free_margin": self.free_margin,
                "profit": 0,
            }
        
        account_info = mt5.account_info()
        if account_info:
            self.balance = account_info.balance
            self.equity = account_info.equity
            self.margin = account_info.margin
            self.free_margin = account_info.margin_free

            return {
                "balance": account_info.balance,
                "equity": account_info.equity,
                "margin": account_info.margin,
                "free_margin": account_info.margin_free,
                "profit": account_info.profit,
            }
        else:
            return {
                "balance": self.balance,
                "equity": self.equity,
                "margin": self.margin,
                "free_margin": self.free_margin,
                "profit": 0,
            }