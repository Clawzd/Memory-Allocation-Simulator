"""Bottom status bar: live, compact summary of current state."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class StatusBar(ttk.Frame):
    def __init__(self, parent, *, palette: dict, **kwargs) -> None:
        super().__init__(parent, style="Card.TFrame", padding=(12, 6), **kwargs)
        self.palette = palette

        self.left_var = tk.StringVar(value="Ready")
        self.center_var = tk.StringVar(value="")
        self.right_var = tk.StringVar(value="\u2328 Ctrl+K  \u00b7  press Space to play")

        ttk.Label(self, textvariable=self.left_var,
                  style="Card.TLabel",
                  font=("Segoe UI", 9)).pack(side="left")
        ttk.Label(self, textvariable=self.center_var,
                  style="Muted.TLabel",
                  font=("Consolas", 9)).pack(side="left", padx=(18, 0))
        ttk.Label(self, textvariable=self.right_var,
                  style="Muted.TLabel",
                  font=("Segoe UI", 8)).pack(side="right")

    def set_ready(self) -> None:
        self.left_var.set("\u25cf Ready")

    def set_running(self, algorithm: str, step: int, total: int) -> None:
        self.left_var.set(
            f"\u25b6 Running {algorithm}  \u00b7  step {step + 1} / {total}"
        )

    def set_live(self, what: str) -> None:
        self.left_var.set(f"\u26a1 LIVE edit: {what}")

    def set_metrics(self, used: int, total: int, util: float, frag: float) -> None:
        self.center_var.set(
            f"Mem {used}/{total} KB  \u00b7  util {util:.1f}%  \u00b7  frag {frag:.1f}%"
        )
