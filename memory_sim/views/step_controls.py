"""Step navigation bar (Prev / Next / Play-Pause / Restart + speed).

Mirrors ``OS-Project/src/components/simulator/StepControls.jsx``.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable


class StepControls(ttk.Frame):
    def __init__(
        self,
        parent,
        *,
        palette: dict,
        on_prev: Callable[[], None],
        on_next: Callable[[], None],
        on_toggle_play: Callable[[], None],
        on_restart: Callable[[], None],
        on_speed_change: Callable[[int], None],
        **kwargs,
    ) -> None:
        super().__init__(parent, style="Card.TFrame", padding=12, **kwargs)
        self._on_prev = on_prev
        self._on_next = on_next
        self._on_toggle = on_toggle_play
        self._on_restart = on_restart
        self._on_speed = on_speed_change

        self.current_step = tk.IntVar(value=0)
        self.total_steps = tk.IntVar(value=0)
        self.playing = tk.BooleanVar(value=False)
        self.speed_ms = tk.IntVar(value=1000)

        self._build()

    def _build(self) -> None:
        top = ttk.Frame(self, style="Card.TFrame")
        top.pack(fill="x")

        self.label_var = tk.StringVar(value="Step 0 / 0")
        ttk.Label(top, textvariable=self.label_var,
                  style="Card.TLabel", font=("Segoe UI", 9, "bold")
                  ).pack(side="left")

        btns = ttk.Frame(top, style="Card.TFrame")
        btns.pack(side="right")
        ttk.Button(btns, text="\u23ee Restart", command=self._on_restart).pack(
            side="left", padx=2
        )
        ttk.Button(btns, text="\u25c0 Prev", command=self._on_prev).pack(
            side="left", padx=2
        )
        self.play_btn = ttk.Button(
            btns, text="\u25b6 Play", style="Primary.TButton",
            command=self._toggle,
        )
        self.play_btn.pack(side="left", padx=2)
        ttk.Button(btns, text="Next \u25b6", command=self._on_next).pack(
            side="left", padx=2
        )

        speed_row = ttk.Frame(self, style="Card.TFrame")
        speed_row.pack(fill="x", pady=(8, 0))
        ttk.Label(speed_row, text="Speed:", style="Muted.TLabel").pack(side="left")
        scale = ttk.Scale(
            speed_row, from_=200, to=2000,
            variable=self.speed_ms, orient="horizontal",
            command=lambda _v: self._on_speed(int(float(self.speed_ms.get()))),
        )
        scale.pack(side="left", fill="x", expand=True, padx=8)
        self.speed_var = tk.StringVar(value="1000 ms")
        ttk.Label(speed_row, textvariable=self.speed_var,
                  style="Muted.TLabel", font=("Consolas", 9)).pack(side="right")
        self.speed_ms.trace_add(
            "write", lambda *_: self.speed_var.set(f"{self.speed_ms.get()} ms")
        )

    def _toggle(self) -> None:
        self._on_toggle()

    # ------------------------------------------------------------------
    def set_state(self, current: int, total: int, playing: bool) -> None:
        self.current_step.set(current)
        self.total_steps.set(total)
        self.playing.set(playing)
        self.label_var.set(f"Step {max(0, current + 1)} / {total}")
        self.play_btn.configure(text="\u23f8 Pause" if playing else "\u25b6 Play")
