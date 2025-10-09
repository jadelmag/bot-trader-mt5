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


class ATRTooltipHandler:
    """Maneja el tooltip para el indicador ATR"""
    
    def __init__(self, ax, canvas):
        self.ax = ax
        self.canvas = canvas
        self.tooltip = None
        self.atr_data = None
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
    
    def update_data(self, atr_data, timestamps):
        """Actualiza los datos para el tooltip"""
        self.atr_data = atr_data
        self.timestamps = timestamps
        self._create_tooltip()
    
    def _on_motion(self, event):
        """Maneja eventos de movimiento del mouse"""
        if event.inaxes != self.ax or self.atr_data is None:
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
        if idx < 0 or idx >= len(self.atr_data):
            self._hide_tooltip()
            return
        
        # Verificar si está cerca de la línea ATR
        atr_value = self.atr_data[idx]
        if np.isnan(atr_value):
            self._hide_tooltip()
            return
        
        # Tolerancia para mostrar el tooltip
        y_range = self.ax.get_ylim()
        tolerance = 0.05 * (y_range[1] - y_range[0])
        
        if abs(y - atr_value) <= tolerance:
            timestamp = self.timestamps[idx]
            text = self._format_atr_tooltip(atr_value, timestamp)
            self._show_tooltip((x, atr_value), text)
        else:
            self._hide_tooltip()
    
    def _format_atr_tooltip(self, atr_value, timestamp):
        """Formatea el texto del tooltip del ATR"""
        return (
            f"Average True Range\n"
            f"{timestamp:%d %b %Y %H:%M}\n"
            f"Valor: {atr_value:.5f}"
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


class BodyATR(ttk.Frame):
    def __init__(self, parent, app, symbol="EURUSD", timeframe="M5", bars=300, logger=None, debug_mode_var=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        
        self.app = app
        self.symbol = symbol
        self.timeframe = timeframe
        self.bars = bars
        self.logger = logger
        self.debug_mode_var = debug_mode_var
        
        self._after_job = None
        self.atr_data = None
        self.timestamps = None
        self.atr_line = None
        
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
        self.tooltip_handler = ATRTooltipHandler(self.ax, self.canvas)
        
        self._draw_placeholder("Cargando ATR...")
    
    def destroy(self):
        self._stop_updates()
        if self.tooltip_handler:
            self.tooltip_handler.disconnect()
        return super().destroy()
    
    def update_atr_data(self, candles_df):
        """Actualiza el gráfico ATR con nuevos datos de velas"""
        if candles_df is None or candles_df.empty:
            return
        
        try:
            # Calcular ATR usando pandas_ta
            import pandas_ta as ta
            atr = ta.atr(candles_df['High'], candles_df['Low'], candles_df['Close'], length=14)
            
            if atr is None or atr.empty:
                return
            
            self.atr_data = atr.values
            self.timestamps = candles_df.index
            
            # Renderizar el gráfico
            self._render_atr_chart()
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error al calcular ATR: {e}")
    
    def _render_atr_chart(self):
        """Renderiza el gráfico ATR"""
        if self.atr_data is None or len(self.atr_data) == 0:
            return
        
        self.ax.clear()
        self.fig.patch.set_facecolor('black')
        self.ax.set_facecolor('black')
        
        # Configurar grid
        self.ax.grid(True, which='both', axis='both', color='#444444', linestyle='--', linewidth=0.6)
        
        # Configurar ejes
        # El ATR no tiene límites fijos, se ajusta automáticamente
        self.ax.set_ylabel('ATR', color='#aaaaaa', fontsize=9)
        self.ax.tick_params(axis='x', colors='#aaaaaa', labelsize=8)
        self.ax.tick_params(axis='y', colors='#aaaaaa', labelsize=8)
        
        # Crear índices para el eje X
        indices = np.arange(len(self.atr_data))
        
        # Dibujar línea ATR
        valid_mask = ~np.isnan(self.atr_data)
        if np.any(valid_mask):
            self.atr_line = self.ax.plot(
                indices[valid_mask],
                self.atr_data[valid_mask],
                color='#00bfff',  # Color azul cielo
                linewidth=1.5,
                label='ATR(14)',
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
            self.tooltip_handler.update_data(self.atr_data, self.timestamps)
        
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
        """Limpia el gráfico ATR"""
        self._draw_placeholder("Sin datos ATR")