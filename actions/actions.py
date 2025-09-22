from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple, Callable

from matplotlib.backend_bases import MouseButton
from matplotlib.patches import Rectangle


@dataclass
class _PanState:
    x0: float
    y0: float
    xlim: Tuple[float, float]
    ylim: Tuple[float, float]


class ChartActions:
    """
    Attach interactive actions to a Matplotlib canvas/axes:
    - Wheel: zoom in/out centered at cursor
    - Left drag: rectangle zoom (dashed gray box); release applies zoom
    - Right drag: pan
    - Double middle click: reset to initial view
    """

    def __init__(self, canvas, ax, on_zoom_pan: Callable[[], None] = None):
        self.canvas = canvas
        self.ax = ax
        self.on_zoom_pan = on_zoom_pan

        self._rect: Optional[Rectangle] = None
        self._pan_state: Optional[_PanState] = None
        self._initial_xlim: Optional[Tuple[float, float]] = None
        self._initial_ylim: Optional[Tuple[float, float]] = None

        self._cid_scroll = canvas.mpl_connect("scroll_event", self._on_scroll)
        self._cid_press = canvas.mpl_connect("button_press_event", self._on_press)
        self._cid_release = canvas.mpl_connect("button_release_event", self._on_release)
        self._cid_motion = canvas.mpl_connect("motion_notify_event", self._on_motion)

    # ---- public API ----
    def set_initial_view(self, xlim: Tuple[float, float], ylim: Tuple[float, float]):
        self._initial_xlim = xlim
        self._initial_ylim = ylim

    def reset_view(self):
        if self._initial_xlim and self._initial_ylim:
            self.ax.set_xlim(self._initial_xlim)
            self.ax.set_ylim(self._initial_ylim)
            self.canvas.draw_idle()
            if self.on_zoom_pan:
                self.on_zoom_pan(is_reset=True)

    # ---- event handlers ----
    def _on_scroll(self, event):
        if event.inaxes != self.ax:
            return
        # Zoom factor: wheel up -> zoom in, wheel down -> zoom out
        base_scale = 1.2
        scale = 1 / base_scale if event.button == 'up' else base_scale

        xdata = event.xdata
        ydata = event.ydata
        xlim = list(self.ax.get_xlim())
        ylim = list(self.ax.get_ylim())

        new_width = (xlim[1] - xlim[0]) * scale
        new_height = (ylim[1] - ylim[0]) * scale

        relx = (xdata - xlim[0]) / (xlim[1] - xlim[0]) if (xlim[1] - xlim[0]) else 0.5
        rely = (ydata - ylim[0]) / (ylim[1] - ylim[0]) if (ylim[1] - ylim[0]) else 0.5

        xlim[0] = xdata - relx * new_width
        xlim[1] = xlim[0] + new_width
        ylim[0] = ydata - rely * new_height
        ylim[1] = ylim[0] + new_height

        self.ax.set_xlim(xlim)
        self.ax.set_ylim(ylim)
        self.canvas.draw_idle()
        if self.on_zoom_pan:
            self.on_zoom_pan()

    def _on_press(self, event):
        if event.inaxes != self.ax:
            return
        # Double middle click: reset
        if event.button == MouseButton.MIDDLE and getattr(event, 'dblclick', False):
            self.reset_view()
            return

        if event.button == MouseButton.LEFT:
            # start rectangle selection
            self._start_rect(event)
        elif event.button == MouseButton.RIGHT:
            # start pan
            self._pan_state = _PanState(event.xdata, event.ydata, self.ax.get_xlim(), self.ax.get_ylim())

    def _on_motion(self, event):
        if event.inaxes != self.ax:
            return
        # update rectangle
        if self._rect is not None and event.button == MouseButton.LEFT:
            self._update_rect(event)
            self.canvas.draw_idle()
        # update pan
        if self._pan_state is not None and event.button == MouseButton.RIGHT:
            self._apply_pan(event)
            self.canvas.draw_idle()

    def _on_release(self, event):
        if event.inaxes != self.ax:
            # clear any transient state regardless
            self._finish_rect(apply_zoom=False)
            self._pan_state = None
            return
        if event.button == MouseButton.LEFT:
            # apply rectangle zoom
            self._finish_rect(apply_zoom=True)
        elif event.button == MouseButton.RIGHT:
            # finish panning
            self._pan_state = None

    # ---- helpers ----
    def _start_rect(self, event):
        self._finish_rect(apply_zoom=False)
        self._rect = Rectangle((event.xdata, event.ydata), 0, 0,
                               linewidth=1.0, edgecolor='#aaaaaa', facecolor='none',
                               linestyle='--')
        self.ax.add_patch(self._rect)
        self._rect._x0 = event.xdata
        self._rect._y0 = event.ydata

    def _update_rect(self, event):
        x0, y0 = self._rect._x0, self._rect._y0
        x1, y1 = event.xdata, event.ydata
        if x1 is None or y1 is None:
            return
        xmin, xmax = sorted([x0, x1])
        ymin, ymax = sorted([y0, y1])
        self._rect.set_bounds(xmin, ymin, xmax - xmin, ymax - ymin)

    def _finish_rect(self, apply_zoom: bool):
        rect = self._rect
        self._rect = None
        if rect is None:
            return
        try:
            x, y, w, h = rect.get_x(), rect.get_y(), rect.get_width(), rect.get_height()
            rect.remove()
        except Exception:
            return
        if apply_zoom and w > 0 and h > 0:
            self.ax.set_xlim((x, x + w))
            self.ax.set_ylim((y, y + h))
            self.canvas.draw_idle()
            if self.on_zoom_pan:
                self.on_zoom_pan()

    def _apply_pan(self, event):
        if self._pan_state is None:
            return
        x0, y0 = self._pan_state.x0, self._pan_state.y0
        xlim0 = self._pan_state.xlim
        ylim0 = self._pan_state.ylim
        if event.xdata is None or event.ydata is None:
            return
        dx = event.xdata - x0
        dy = event.ydata - y0
        self.ax.set_xlim((xlim0[0] - dx, xlim0[1] - dx))
        self.ax.set_ylim((ylim0[0] - dy, ylim0[1] - dy))
        if self.on_zoom_pan:
            self.on_zoom_pan()