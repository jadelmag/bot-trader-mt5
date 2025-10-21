import tkinter as tk
from tkinter import ttk
from datetime import datetime


# Semantic color mapping for convenience names
COLOR_MAP = {
    "info": "#9cdcfe",
    "success": "#6A9955",
    "error": "#F44747",
    "warn": "#D7BA7D",
}


class BodyLogger(ttk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # Scrollable text area
        self.text = tk.Text(
            self,
            wrap="word",
            state="disabled",
            background="#0f0f0f",
            foreground="#e6e6e6",
            insertbackground="#e6e6e6",
            height=15,
            padx=8,
            pady=6,
        )
        self.text.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.text.configure(yscrollcommand=scrollbar.set)

        # Tags for colorized lines
        self.text.tag_configure("INFO", foreground="#9cdcfe")
        self.text.tag_configure("SUCCESS", foreground="#6A9955")
        self.text.tag_configure("ERROR", foreground="#F44747")
        self.text.tag_configure("WARN", foreground="#D7BA7D")
        self.text.tag_configure("TIME", foreground="#888888")

    def _resolve_color(self, value: str) -> str | None:
        """Return a Tk-acceptable color string or None if invalid.

        Accepts hex colors (e.g., #RRGGBB), any Tk color name, or our semantic
        names defined in COLOR_MAP (e.g., 'info', 'success', 'error', 'warn').
        """
        if not value:
            return None
        candidate = COLOR_MAP.get(value.strip().lower(), value)
        try:
            # Validate color with Tk; raises TclError if unknown
            self.winfo_rgb(candidate)
            return candidate
        except tk.TclError:
            return None

    def _append(self, message: str, tag: str = "INFO", color: str = None):
        """Añade un mensaje al log. Si se proporciona 'color', se usa para una etiqueta dinámica."""
        # Ensure thread-safe UI update
        def _write():
            self.text.configure(state="normal")
            now = datetime.now().strftime("%H:%M:%S")
            self.text.insert("end", f"[{now}] ", ("TIME",))

            # Usar color personalizado si se proporciona
            final_tag = tag
            if color:
                lc = color.lower()
                if color.startswith("#"):
                    custom_tag = f"custom_{color.replace('#', '')}"
                    self.text.tag_configure(custom_tag, foreground=color)
                    final_tag = custom_tag
                else:
                    tag_map = {"info": "INFO", "success": "SUCCESS", "error": "ERROR", "warn": "WARN"}
                    final_tag = tag_map.get(lc, tag)
            else:
                final_tag = tag

            self.text.insert("end", message + "\n", (final_tag,))
            self.text.see("end")
            self.text.configure(state="disabled")
        self.after(0, _write)

    def log(self, message: str, color: str = None):
        """Registra un mensaje informativo, con un color opcional."""
        self._append(message, "INFO", color=color)

    def success(self, message: str):
        self._append(message, "SUCCESS")

    def error(self, message: str):
        self._append(message, "ERROR")

    def warn(self, message: str):
        self._append(message, "WARN")

    def log_summary(self, success_msg: str, error_msg: str):
        """Muestra un resumen con un mensaje de éxito y uno de error."""
        self.success(success_msg)
        self.error(error_msg)

    def clear_log(self):
        """Borra todo el contenido del logger."""
        self.text.configure(state="normal")
        self.text.delete('1.0', tk.END)
        self.text.configure(state="disabled")

    def get_content(self) -> str:
        """Devuelve todo el contenido del widget de texto."""
        return self.text.get('1.0', tk.END)