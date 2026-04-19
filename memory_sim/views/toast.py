"""Transient toast notifications.

Mirrors the website's ``use-toast.js`` behaviour: a small banner that
pops up in the bottom-right of the main window and auto-dismisses.
"""

from __future__ import annotations

import tkinter as tk


class ToastManager:
    def __init__(self, root, palette: dict) -> None:
        self.root = root
        self.palette = palette
        self._queue: list[tk.Toplevel] = []

    def show(self, title: str, description: str = "",
             variant: str = "default", duration_ms: int = 2500) -> None:
        tip = tk.Toplevel(self.root)
        tip.wm_overrideredirect(True)
        tip.attributes("-topmost", True)

        color_map = {
            "default":    (self.palette["card"], self.palette["foreground"]),
            "success":    (self.palette["success"], "#ffffff"),
            "destructive":(self.palette["danger"], "#ffffff"),
            "warning":    (self.palette["warning"], "#0b1220"),
        }
        bg, fg = color_map.get(variant, color_map["default"])

        frame = tk.Frame(
            tip, bg=bg, highlightthickness=1,
            highlightbackground=self.palette["border"],
        )
        frame.pack()
        tk.Label(frame, text=title, bg=bg, fg=fg,
                 font=("Segoe UI", 10, "bold"),
                 anchor="w", justify="left",
                 padx=14).pack(fill="x", pady=(8, 0))
        if description:
            tk.Label(frame, text=description, bg=bg, fg=fg,
                     font=("Segoe UI", 9), anchor="w", justify="left",
                     padx=14, wraplength=280).pack(fill="x", pady=(2, 8))
        else:
            tk.Frame(frame, bg=bg, height=8).pack()

        self.root.update_idletasks()
        w = tip.winfo_width() or 280
        h = tip.winfo_height() or 48
        rx = self.root.winfo_rootx() + self.root.winfo_width() - w - 24
        ry = self.root.winfo_rooty() + self.root.winfo_height() - h - 24
        tip.geometry(f"+{rx}+{ry}")

        tip.after(duration_ms, tip.destroy)
