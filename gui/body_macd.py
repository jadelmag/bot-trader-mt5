from tkinter import ttk
import pandas as pd
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib import dates as mdates
import threading

try:
    import MetaTrader5 as mt5
except Exception:
    mt5 = None


class MACDTooltipHandler:
    """Maneja el tooltip para el indicador MACD"""
    
    def __init__(self, ax, canvas):
        self.ax = ax
        self.canvas = canvas
        self.tooltip = None
        self.macd_data = None
        self.signal_data = None
        self.histogram_data = None
        self.timestamps = None
        
        # Crear tooltip inicial
        self._create_tooltip()
        
        # Conectar eventos del mouse
        self._cid_motion = canvas.mpl_connect("motion_notify_event", self._on_motion)
        self._cid_leave = canvas.mpl_connect("axes_leave_event", self._on_leave)
    
    def _create_tooltip(self):
        """Crea o recrea el tooltip"""
        self.tooltip = self.ax.annotate(
            "",
            xy=(0, 0),
            xytext=(15, 15),
            textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.3", fc="#222222", ec="#888888", lw=0.5),
            color="#dddddd",
            fontsize=9,
            visible=False,
            zorder=1000,
        )
    
    def update_data(self, macd_data, signal_data, histogram_data, timestamps):
        """Actualiza los datos para el tooltip"""
        self.macd_data = macd_data
        self.signal_data = signal_data
        self.histogram_data = histogram_data
        self.timestamps = timestamps
        self._create_tooltip()
    
    def _on_motion(self, event):
        """Maneja eventos de movimiento del mouse"""
        if event.inaxes != self.ax or self.macd_data is None:
            self._hide_tooltip()
            return
        
        # Posicionamiento dinámico del tooltip
        canvas_width, canvas_height = self.canvas.get_width_height()
        
        if event.x > canvas_width / 2:
            self.tooltip.set_horizontalalignment('right')
            x_offset = -20
        else:
            self.tooltip.set_horizontalalignment('left')
            x_offset = 20
        
        if event.y > canvas_height / 2:
            y_offset = -40
        else:
            y_offset = 20
        
        self.tooltip.xyann = (x_offset, y_offset)
        
        x = event.xdata
        y = event.ydata
        if x is None or y is None:
            self._hide_tooltip()
            return
        
        # Encontrar el punto más cercano
        idx = int(round(x))
        if idx < 0 or idx >= len(self.macd_data):
            self._hide_tooltip()
            return
        
        # Verificar si está cerca de alguna línea
        macd_value = self.macd_data[idx]
        signal_value = self.signal_data[idx]
        
        if np.isnan(macd_value) and np.isnan(signal_value):
            self._hide_tooltip()
            return
        
        # Tolerancia para mostrar el tooltip
        y_range = self.ax.get_ylim()
        tolerance = 0.05 * (y_range[1] - y_range[0])
        
        # Verificar cercanía a línea MACD o señal
        show_tooltip = False
        if not np.isnan(macd_value) and abs(y - macd_value) <= tolerance:
            show_tooltip = True
        elif not np.isnan(signal_value) and abs(y - signal_value) <= tolerance:
            show_tooltip = True
        
        if show_tooltip:
            timestamp = self.timestamps[idx]
            text = self._format_macd_tooltip(macd_value, signal_value, timestamp)
            # Usar la posición de la línea MACD para el tooltip
            tooltip_y = macd_value if not np.isnan(macd_value) else signal_value
            self._show_tooltip((x, tooltip_y), text)
        else:
            self._hide_tooltip()
    
    def _format_macd_tooltip(self, macd_value, signal_value, timestamp):
        """Formatea el texto del tooltip del MACD"""
        return (
            f"MACD(12, 26, 9)\n"
            f"{timestamp:%d %b %Y %H:%M}\n"
            f"MACD: {macd_value:.5f}\n"
            f"Signal: {signal_value:.5f}"
        )
    
    def _show_tooltip(self, xy_data, text):
        """Muestra el tooltip en la posición especificada"""
        if self.tooltip is None:
            return
        self.tooltip.xy = xy_data
        self.tooltip.set_text(text)
        self.tooltip.set_visible(True)
        self.tooltip.set_zorder(1000)
        self.canvas.draw_idle()
    
    def _hide_tooltip(self):
        """Oculta el tooltip"""
        if self.tooltip and self.tooltip.get_visible():
            self.tooltip.set_visible(False)
            self.canvas.draw_idle()
    
    def _on_leave(self, event):
        """Maneja eventos de salida del mouse"""
        self._hide_tooltip()
    
    def disconnect(self):
        """Desconecta los manejadores de eventos"""
        try:
            self.canvas.mpl_disconnect(self._cid_motion)
            self.canvas.mpl_disconnect(self._cid_leave)
        except Exception:
            pass


class BodyMACD(ttk.Frame):
    def __init__(self, parent, app, symbol="EURUSD", timeframe="M5", bars=300, logger=None, debug_mode_var=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        
        self.app = app
        self.symbol = symbol
        self.timeframe = timeframe
        self.bars = bars
        self.logger = logger
        self.debug_mode_var = debug_mode_var
        
        self._after_job = None
        self.macd_data = None
        self.signal_data = None
        self.histogram_data = None
        self.timestamps = None
        self.macd_line = None
        self.signal_line = None
        
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        
        # Crear figura de matplotlib
        self.fig = Figure(figsize=(8, 2), dpi=100)
        self.ax = self.fig.add_subplot(111)
        
        # Estilo oscuro
        self.fig.patch.set_facecolor('black')
        self.ax.set_facecolor('black')
        
        # Canvas de matplotlib
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.grid(row=0, column=0, sticky="nsew")
        
        # Tooltip handler
        self.tooltip_handler = MACDTooltipHandler(self.ax, self.canvas)
        
        self._draw_placeholder("Cargando MACD...")
    
    def destroy(self):
        self._stop_updates()
        if self.tooltip_handler:
            self.tooltip_handler.disconnect()
        return super().destroy()
    
    def update_macd_data(self, candles_df):
        """Actualiza el gráfico MACD con nuevos datos de velas"""
        if candles_df is None or candles_df.empty:
            return
        
        try:
            # Calcular MACD usando pandas_ta
            import pandas_ta as ta
            macd_result = ta.macd(candles_df['Close'], fast=12, slow=26, signal=9)
            
            if macd_result is None or macd_result.empty:
                return
            
            # pandas_ta retorna un DataFrame con columnas: MACD_12_26_9, MACDh_12_26_9, MACDs_12_26_9
            self.macd_data = macd_result[f'MACD_12_26_9'].values
            self.signal_data = macd_result[f'MACDs_12_26_9'].values
            self.histogram_data = macd_result[f'MACDh_12_26_9'].values
            self.timestamps = candles_df.index
            
            # Renderizar el gráfico
            self._render_macd_chart()
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error al calcular MACD: {e}")
    
    def _render_macd_chart(self):
        """Renderiza el gráfico MACD"""
        if self.macd_data is None or len(self.macd_data) == 0:
            return
        
        self.ax.clear()
        self.fig.patch.set_facecolor('black')
        self.ax.set_facecolor('black')
        
        # Configurar grid
        self.ax.grid(True, which='both', axis='both', color='#444444', linestyle='--', linewidth=0.6)
        
        # Configurar ejes
        self.ax.set_ylabel('MACD', color='#aaaaaa', fontsize=9)
        self.ax.tick_params(axis='x', colors='#aaaaaa', labelsize=8)
        self.ax.tick_params(axis='y', colors='#aaaaaa', labelsize=8)
        
        # Línea de cero
        self.ax.axhline(y=0, color='#888888', linestyle='-', linewidth=0.5, alpha=0.5)
        
        # Crear índices para el eje X
        indices = np.arange(len(self.macd_data))
        
        # Dibujar histograma
        valid_hist_mask = ~np.isnan(self.histogram_data)
        if np.any(valid_hist_mask):
            colors = ['#26a69a' if h >= 0 else '#ef5350' for h in self.histogram_data[valid_hist_mask]]
            self.ax.bar(
                indices[valid_hist_mask],
                self.histogram_data[valid_hist_mask],
                color=colors,
                alpha=0.3,
                width=0.8,
                label='Histogram',
                zorder=5
            )
        
        # Dibujar línea MACD
        valid_macd_mask = ~np.isnan(self.macd_data)
        if np.any(valid_macd_mask):
            self.macd_line = self.ax.plot(
                indices[valid_macd_mask],
                self.macd_data[valid_macd_mask],
                color='#2196f3',  # Azul
                linewidth=1.5,
                label='MACD',
                zorder=10
            )[0]
        
        # Dibujar línea de señal
        valid_signal_mask = ~np.isnan(self.signal_data)
        if np.any(valid_signal_mask):
            self.signal_line = self.ax.plot(
                indices[valid_signal_mask],
                self.signal_data[valid_signal_mask],
                color='#ff9800',  # Naranja
                linewidth=1.5,
                label='Signal',
                zorder=10
            )[0]
        
        # Leyenda
        legend = self.ax.legend(loc='upper left', fontsize=7, framealpha=0.3, facecolor='#fff', edgecolor='#fff')
        legend.set_zorder(11)
        
        # Formatear eje X con fechas
        if len(self.timestamps) > 0:
            # Mostrar solo algunas etiquetas para evitar saturación
            step = max(1, len(self.timestamps) // 10)
            tick_positions = indices[::step]
            tick_labels = [self.timestamps[i].strftime('%H:%M') for i in tick_positions]
            self.ax.set_xticks(tick_positions)
            self.ax.set_xticklabels(tick_labels, rotation=0)
        
        # Actualizar tooltip handler
        if self.tooltip_handler:
            self.tooltip_handler.update_data(self.macd_data, self.signal_data, self.histogram_data, self.timestamps)
        
        self.fig.tight_layout()
        self.canvas.draw()
    
    def _draw_placeholder(self, text):
        """Dibuja un placeholder cuando no hay datos"""
        self.ax.clear()
        self.fig.patch.set_facecolor('black')
        self.ax.set_facecolor('black')
        self.ax.grid(False)
        self.ax.text(
            0.5, 0.5, text,
            ha="center", va="center",
            transform=self.ax.transAxes,
            fontsize=10,
            color="#bbbbbb"
        )
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.fig.tight_layout()
        self.canvas.draw()
    
    def _stop_updates(self):
        """Detiene las actualizaciones programadas"""
        if self._after_job is not None:
            try:
                self.after_cancel(self._after_job)
            except Exception:
                pass
            self._after_job = None
    
    def clear(self):
        """Limpia el gráfico MACD"""
        self._draw_placeholder("Sin datos MACD")