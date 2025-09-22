import numpy as np
from typing import Optional
import pandas as pd


class TooltipHandler:
    """Handles tooltip display for chart candles and moving average"""
    
    def __init__(self, ax, canvas):
        self.ax = ax
        self.canvas = canvas
        self.tooltip = None
        self.df: Optional[pd.DataFrame] = None
        self.ma: Optional[pd.Series] = None
        
        # Create initial tooltip annotation
        self._create_tooltip()
        
        # Connect mouse events
        self._cid_motion = canvas.mpl_connect("motion_notify_event", self._on_motion)
        self._cid_leave = canvas.mpl_connect("axes_leave_event", self._on_leave)
    
    def _create_tooltip(self):
        """Create or recreate the tooltip annotation"""
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
    
    def update_data(self, df: pd.DataFrame, ma: Optional[pd.Series]):
        """Update the data for tooltip display"""
        self.df = df
        self.ma = ma
        # Recreate tooltip after ax.clear()
        self._create_tooltip()
    
    def _on_motion(self, event):
        """Handle mouse motion events"""
        if event.inaxes != self.ax or self.df is None:
            self._hide_tooltip()
            return
        
        # --- Lógica de posicionamiento dinámico del tooltip ---
        canvas_width, canvas_height = self.canvas.get_width_height()

        # Posicionamiento Horizontal
        if event.x > canvas_width / 2:
            self.tooltip.set_horizontalalignment('right')
            x_offset = -20 # Mover a la izquierda
        else:
            self.tooltip.set_horizontalalignment('left')
            x_offset = 20 # Mover a la derecha

        # Posicionamiento Vertical (event.y en matplotlib es desde abajo)
        if event.y > canvas_height / 2:
            y_offset = -40 # Mover hacia abajo
        else:
            y_offset = 20 # Mover hacia arriba

        self.tooltip.xyann = (x_offset, y_offset)

        x = event.xdata
        y = event.ydata
        if x is None or y is None:
            self._hide_tooltip()
            return
        
        # Find nearest candle by x (mplfinance uses integer indices)
        idx = int(round(x))
        if idx < 0 or idx >= len(self.df):
            self._hide_tooltip()
            return
        
        t = self.df.index[idx]
        row = self.df.iloc[idx]
        
        # Determine if cursor is near MA line
        near_ma = self._is_near_ma(idx, y)
        
        # Build and show appropriate tooltip
        if near_ma:
            text = self._format_ma_tooltip(t, idx)
            self._show_tooltip((x, self.ma.iloc[idx]), text)
        else:
            text = self._format_candle_tooltip(t, row)
            self._show_tooltip((x, row['Close']), text)
    
    def _is_near_ma(self, idx: int, y: float) -> bool:
        """Check if cursor is near the MA line"""
        if self.ma is None or idx >= len(self.ma) or np.isnan(self.ma.iloc[idx]):
            return False
        
        y_ma = float(self.ma.iloc[idx])
        rng = self.ax.get_ylim()
        tol = 0.01 * (rng[1] - rng[0])  # 1% of price range tolerance
        return abs(y - y_ma) <= tol
    
    def _format_ma_tooltip(self, timestamp, idx: int) -> str:
        """Format moving average tooltip text"""
        return (
            f"Moving Average\n"
            f"{timestamp:%d %b %Y %H:%M}\n"
            f"{self.ma.iloc[idx]:.5f}"
        )
    
    def _format_candle_tooltip(self, timestamp, row) -> str:
        """Format candle OHLCV tooltip text"""
        volume = row.get('Volume', row.get('tick_volume', 0))
        return (
            f"{timestamp:%d %b %Y %H:%M}\n"
            f"Open:  {row['Open']:.5f}\n"
            f"High:  {row['High']:.5f}\n"
            f"Low:   {row['Low']:.5f}\n"
            f"Close: {row['Close']:.5f}\n"
            f"Volume: {volume:,.0f}"
        )
    
    def _show_tooltip(self, xy_data, text: str):
        """Show tooltip at specified position with given text"""
        if self.tooltip is None:
            return
        self.tooltip.xy = xy_data
        self.tooltip.set_text(text)
        self.tooltip.set_visible(True)
        self.tooltip.set_zorder(1000)
        self.canvas.draw_idle()
    
    def _hide_tooltip(self):
        """Hide the tooltip"""
        if self.tooltip and self.tooltip.get_visible():
            self.tooltip.set_visible(False)
            self.canvas.draw_idle()
    
    def _on_leave(self, event):
        """Handle mouse leave events"""
        self._hide_tooltip()
    
    def disconnect(self):
        """Disconnect mouse event handlers"""
        try:
            self.canvas.mpl_disconnect(self._cid_motion)
            self.canvas.mpl_disconnect(self._cid_leave)
        except Exception:
            pass