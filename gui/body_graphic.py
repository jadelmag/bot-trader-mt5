from tkinter import ttk

import pandas as pd
import mplfinance as mpf
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib import dates as mdates
import numpy as np
import threading

try:
    import MetaTrader5 as mt5
except Exception:
    mt5 = None

try:
    from actions.actions import ChartActions
except Exception:
    ChartActions = None

try:
    from actions.tooltip import TooltipHandler
except Exception:
    TooltipHandler = None


class BodyGraphic(ttk.Frame):
    def __init__(self, parent, app, symbol: str = "EURUSD", timeframe: str = "M5", bars: int = 300, logger=None, debug_mode_var=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.app = app
        self.symbol = symbol
        self.timeframe = timeframe
        self.bars = bars
        self.logger = logger
        self.debug_mode_var = debug_mode_var

        self._after_job = None
        self.price_line = None
        self.price_text = None
        self.candles_df: pd.DataFrame | None = None
        self.realtime_data = [] # Para almacenar datos de la simulación
        self.ma: pd.Series | None = None
        self.is_zoomed = False # Para rastrear si el usuario ha hecho zoom/pan

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.fig = Figure(figsize=(8, 4), dpi=100)
        self.ax = self.fig.add_subplot(111)

        self.fig.patch.set_facecolor('black')
        self.ax.set_facecolor('black')

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.grid(row=0, column=0, sticky="nsew")

        self.actions = ChartActions(self.canvas, self.ax, on_zoom_pan=self._set_zoomed_flag) if ChartActions else None

        self.tooltip_handler = TooltipHandler(self.ax, self.canvas) if TooltipHandler else None

        self._draw_placeholder("Cargando gráfico…")

    def destroy(self):
        self._stop_live_updates()
        if self.tooltip_handler:
            self.tooltip_handler.disconnect()
        return super().destroy()

    def load_symbol(self, symbol: str = None, timeframe: str = None, bars: int = None, queue=None):
        if symbol:
            self.symbol = symbol
        if timeframe:
            self.timeframe = timeframe
        if bars:
            self.bars = bars
        
        # Lanzar la carga de datos en un hilo para no bloquear la UI
        if queue:
            thread = threading.Thread(target=self._fetch_chart_data_threaded, args=(queue,), daemon=True)
            thread.start()
        else:
            # Fallback si no se pasa la cola (comportamiento antiguo)
            self.refresh()

    def _fetch_chart_data_threaded(self, queue):
        """Se ejecuta en un hilo para obtener los datos del gráfico y los pone en la cola."""
        try:
            # Al cargar nuevos datos, reseteamos el estado de zoom
            self.is_zoomed = False
            tf = self._mt5_timeframe()
            if tf is None:
                queue.put(("log_error", "Timeframe inválido"))
                return

            rates = mt5.copy_rates_from_pos(self.symbol, tf, 0, self.bars)
            if rates is None or len(rates) == 0:
                queue.put(("log_info", f"No se encontraron datos para {self.symbol}"))
                # Podríamos querer limpiar el gráfico o mostrar un placeholder
                return

            df = pd.DataFrame(rates)
            df["time"] = pd.to_datetime(df["time"], unit="s")
            df = df.set_index("time")
            df.rename(columns={"open": "Open", "high": "High", "low": "Low", "close": "Close", "tick_volume": "Volume"}, inplace=True)
            df.sort_index(inplace=True)
            
            # Enviar los datos listos para renderizar
            queue.put(("chart_data_ready", df))

        except Exception as e:
            queue.put(("log_error", f"Error al cargar datos del gráfico: {e}"))

    def render_chart_data(self, df: pd.DataFrame):
        """Renderiza los datos del gráfico en el hilo principal de la UI."""
        self._stop_live_updates()
        self.candles_df = df

        # --- Guardar estado del zoom --- 
        xlim, ylim = (None, None)
        if self.is_zoomed:
            xlim = self.ax.get_xlim()
            ylim = self.ax.get_ylim()

        self.ax.clear()
        self.fig.patch.set_facecolor('black')
        self.ax.set_facecolor('black')
        self.ax.grid(True, which='both', axis='both', color='#444444', linestyle='--', linewidth=0.6)
        self.ax.yaxis.tick_right()
        self.ax.yaxis.set_label_position("right")
        self.ax.tick_params(axis='x', colors='#aaaaaa', labelrotation=0)
        self.ax.tick_params(axis='y', colors='#aaaaaa')
        self.ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%d %b %H:%M'))

        style = mpf.make_mpf_style(
            base_mpf_style='nightclouds',
            marketcolors=mpf.make_marketcolors(
                up='#26a69a', down='#ef5350',
                edge={'up':'#26a69a','down':'#ef5350'},
                wick={'up':'#26a69a','down':'#ef5350'},
                volume='inherit'
            ),
            facecolor='black', figcolor='black', gridcolor='#404040', gridstyle='--'
        )
        width_cfg = dict(candle_linewidth=1.0, candle_width=0.8, volume_width=0.7)
        mpf.plot(
            df,
            type="candle",
            ax=self.ax,
            volume=False,
            style=style,
            update_width_config=width_cfg,
            datetime_format="%d %b %H:%M",
            xrotation=0,
            show_nontrading=False,
            tight_layout=True
        )

        # Añadir margen a la derecha del gráfico
        current_xlim = self.ax.get_xlim()
        range_width = current_xlim[1] - current_xlim[0]
        # Añadimos un 15% de margen a la derecha, que es un buen compromiso visual
        new_xlim_right = current_xlim[1] + (range_width * 0.15)
        self.ax.set_xlim(current_xlim[0], new_xlim_right)

        period = 20
        if len(df) >= period:
            self.ma = df['Close'].rolling(window=period).mean()
            valid_ma = self.ma.dropna()
            if len(valid_ma) > 0:
                ma_indices = np.arange(len(df))[~self.ma.isna()]
                ma_values = self.ma.dropna().values
                self.ax.plot(ma_indices, ma_values, 
                               color='#ff0000', linewidth=2.0, 
                               label=f'MA({period})', zorder=10)
        else:
            self.ma = None

        if self.tooltip_handler:
            self.tooltip_handler.update_data(self.candles_df, self.ma)

        last_price = float(df['Close'].iloc[-1])
        self.price_line = self.ax.axhline(y=last_price, color='#888888', linestyle='-', linewidth=1.0)
        if self.price_text is not None:
            try:
                self.price_text.remove()
            except Exception:
                pass
        self.price_text = self.ax.text(
            1.0, last_price,
            f"{last_price:.5f}",
            color='#cccccc', fontsize=9,
            ha='left', va='center',
            transform=self.ax.get_yaxis_transform(),
            bbox=dict(boxstyle='round,pad=0.2', facecolor='#222222', edgecolor='#666666', linewidth=0.5)
        )

        self.fig.tight_layout()
        self.canvas.draw()

        # --- Restaurar estado del zoom ---
        if xlim and ylim:
            self.ax.set_xlim(xlim)
            self.ax.set_ylim(ylim)
            self.canvas.draw_idle() # Redibujar con el zoom restaurado

        if self.actions:
            # Si no estábamos haciendo zoom, actualizamos la vista inicial
            if not self.is_zoomed:
                self.actions.set_initial_view(self.ax.get_xlim(), self.ax.get_ylim())

    def start_live_updates(self, interval_ms: int = 50):
        """Inicia el bucle de actualización en vivo con un intervalo específico."""
        self._stop_live_updates() # Asegurarse de que no hay bucles duplicados
        self._schedule_live_update(delay_ms=interval_ms)

    def update_simulation_chart(self, candle_data):
        """Procesa y dibuja los datos de una vela de la simulación."""
        if not candle_data:
            return

        # Convertir el diccionario de la vela a un formato compatible con el DataFrame
        candle_data['time'] = pd.to_datetime(candle_data['time'])
        new_candle = pd.DataFrame([candle_data]).set_index('time')
        new_candle.rename(columns={
            'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'
        }, inplace=True)

        if self.candles_df is None or self.candles_df.empty:
            self.candles_df = new_candle
        else:
            # Si la vela es nueva, la añadimos. Si ya existe, la actualizamos.
            if new_candle.index[0] > self.candles_df.index[-1]:
                self.candles_df = pd.concat([self.candles_df, new_candle])
            else:
                self.candles_df.loc[new_candle.index[0]] = new_candle.iloc[0]
        
        # Mantenemos solo las últimas 'self.bars' velas para que el gráfico no se sature
        if len(self.candles_df) > self.bars:
            self.candles_df = self.candles_df.iloc[-self.bars:]

        # Re-renderizar el gráfico con los datos actualizados
        # No reseteamos el zoom aquí, la propia función render se encarga
        self.render_chart_data(self.candles_df)

    def update_realtime_candle(self, candle_data):
        """Callback para ser llamado desde la simulación. Pone los datos en la cola de la app."""
        self.app.queue.put(("realtime_candle_update", candle_data))

    def _set_zoomed_flag(self, is_reset=False):
        """Callback que se activa con el zoom/pan para mantener el estado."""
        if is_reset:
            self.is_zoomed = False
        else:
            self.is_zoomed = True

    def _mt5_timeframe(self):
        if mt5 is None:
            return None
        mapping = {
            "M1": mt5.TIMEFRAME_M1,
            "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15,
            "M30": mt5.TIMEFRAME_M30,
            "H1": mt5.TIMEFRAME_H1,
            "H4": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1,
        }
        return mapping.get(self.timeframe.upper(), mt5.TIMEFRAME_M5)

    def refresh(self):
        # Ahora 'refresh' simplemente vuelve a lanzar la carga de datos en un hilo
        self.load_symbol(queue=self.app.queue)

    def draw_trades(self, trades):
        """Dibuja marcadores en el gráfico para visualizar las operaciones."""
        if not trades or self.candles_df is None:
            return

        for trade in trades:
            entry_idx = trade['entry_index']
            exit_idx = trade['exit_index']

            # Asegurarse de que los índices están dentro de los límites del dataframe
            if entry_idx >= len(self.candles_df) or exit_idx >= len(self.candles_df):
                continue

            entry_price = trade['entry_price']
            exit_price = trade['exit_price']
            trade_type = trade['type']

            # Marcador de entrada
            if trade_type == 'long':
                self.ax.plot(entry_idx, entry_price, '^', color='lime', markersize=8, label='Compra')
            elif trade_type == 'short':
                self.ax.plot(entry_idx, entry_price, 'v', color='red', markersize=8, label='Venta')

            # Marcador de salida
            self.ax.plot(exit_idx, exit_price, 'o', color='cyan', markersize=5, label='Cierre')

            # Línea conectando entrada y salida
            self.ax.plot([entry_idx, exit_idx], [entry_price, exit_price], linestyle='--', color='yellow', linewidth=0.7)

        # Para evitar etiquetas duplicadas en la leyenda
        handles, labels = self.ax.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        if by_label:
            self.ax.legend(by_label.values(), by_label.keys())

        self.canvas.draw()

    def clear_drawings(self):
        """Elimina todos los dibujos adicionales del gráfico volviéndolo a cargar."""
        self.refresh()

    def _draw_placeholder(self, text: str):
        self.ax.clear()
        self.fig.patch.set_facecolor('black')
        self.ax.set_facecolor('black')
        self.ax.grid(False)
        self.ax.text(0.5, 0.5, text, ha="center", va="center", transform=self.ax.transAxes, fontsize=11, color="#bbbbbb")
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.fig.tight_layout()
        self.canvas.draw()

    def _get_timeframe_delta(self):
        """Convierte el string del timeframe en un objeto pd.Timedelta."""
        mapping = {
            "M1": pd.Timedelta(minutes=1),
            "M5": pd.Timedelta(minutes=5),
            "M15": pd.Timedelta(minutes=15),
            "M30": pd.Timedelta(minutes=30),
            "H1": pd.Timedelta(hours=1),
            "H4": pd.Timedelta(hours=4),
            "D1": pd.Timedelta(days=1),
        }
        return mapping.get(self.timeframe.upper())

    def _schedule_live_update(self, delay_ms: int = 1000):
        if self._after_job is not None:
            try:
                self.after_cancel(self._after_job)
            except Exception:
                pass
            self._after_job = None
        self._after_job = self.after(delay_ms, lambda: self._live_update_once(reschedule_delay=delay_ms))

    def _stop_live_updates(self):
        if self._after_job is not None:
            try:
                self.after_cancel(self._after_job)
            except Exception:
                pass
            self._after_job = None

    def _live_update_once(self, reschedule_delay: int = 1000):
        if mt5 is None:
            return
        try:
            tick = mt5.symbol_info_tick(self.symbol)
            if tick is None:
                self._schedule_live_update(reschedule_delay)
                return

            # --- Lógica de detección de nueva vela ---
            if self.candles_df is not None and not self.candles_df.empty:
                last_candle_time = self.candles_df.index[-1]
                timeframe_delta = self._get_timeframe_delta()
                current_tick_time = pd.to_datetime(tick.time, unit='s')

                if timeframe_delta and current_tick_time >= (last_candle_time + timeframe_delta):
                    if self.logger:
                        self.logger.success(f"Nueva vela detectada para {self.timeframe}. Refrescando gráfico...")
                    self.refresh() # Llama a refresh y termina este ciclo de actualización
                    return
            # --- Fin de la lógica ---

            price = getattr(tick, 'last', None)
            if price is None or price == 0:
                price = getattr(tick, 'bid', None)
            if price is None:
                self._schedule_live_update(reschedule_delay)
                return

            # --- Feed the simulation instance ---
            if self.price_line is None:
                self.price_line = self.ax.axhline(y=price, color='#888888', linestyle='-', linewidth=1.0)
            else:
                self.price_line.set_ydata([price, price])
            if self.price_text is None:
                self.price_text = self.ax.text(
                    1.0, price,
                    f"{price:.5f}",
                    color='#cccccc', fontsize=9,
                    ha='left', va='center',
                    transform=self.ax.get_yaxis_transform(),
                    bbox=dict(boxstyle='round,pad=0.2', facecolor='#222222', edgecolor='#666666', linewidth=0.5)
                )
            else:
                self.price_text.set_position((1.0, price))
                self.price_text.set_text(f"{price:.5f}")
            self.canvas.draw_idle()
        except Exception:
            pass
        finally:
            self._schedule_live_update(reschedule_delay)