"""Polished history sparkline: utilization + external fragmentation.

Design goals:
  * Solid (blended) fills instead of ugly stipple patterns.
  * Left-side Y axis with 0 / 50 / 100 labels.
  * Soft horizontal grid at the same reference values.
  * A vertical "current step" indicator that moves as the user navigates.
  * Small dots on the utilization line marking ALLOCATED / FAILED events
    (green for success, red for failure).
  * Clean value chips on the right, clearly separated.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Iterable, Optional


# ----------------------------- colour helpers ------------------------------

def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(c))) for c in rgb)


def _blend(fg: str, bg: str, alpha: float) -> str:
    """Pre-blend *fg* over *bg* with the given alpha (0..1) so Tk's
    opaque canvas can simulate transparency."""
    fr, fg_, fb = _hex_to_rgb(fg)
    br, bg_, bb = _hex_to_rgb(bg)
    r = fr * alpha + br * (1 - alpha)
    g = fg_ * alpha + bg_ * (1 - alpha)
    b = fb * alpha + bb * (1 - alpha)
    return _rgb_to_hex((r, g, b))


# ----------------------------- widget --------------------------------------


class FragmentationChart(ttk.Frame):
    AXIS_W = 36          # space reserved on the left for Y labels
    RIGHT_W = 90         # space reserved on the right for value chips
    TOP_PAD = 10
    BOTTOM_PAD = 18

    def __init__(
        self,
        parent,
        *,
        palette: dict,
        on_jump: Optional[Callable[[int], None]] = None,
        **kwargs,
    ) -> None:
        super().__init__(parent, style="Card.TFrame", padding=14, **kwargs)
        self.palette = palette
        self._on_jump = on_jump

        header = ttk.Frame(self, style="Card.TFrame")
        header.pack(fill="x")
        ttk.Label(header, text="HISTORY",
                  style="SectionTitle.TLabel").pack(side="left")
        sub = ttk.Label(
            header,
            text="utilization & external fragmentation over simulation steps",
            style="Muted.TLabel",
        )
        sub.pack(side="left", padx=(10, 0))

        legend = ttk.Frame(header, style="Card.TFrame")
        legend.pack(side="right")
        self._legend_chip(legend, palette["primary"], "Utilization")
        self._legend_chip(legend, palette["warning"], "Fragmentation",
                          pad=(10, 0))

        self.canvas = tk.Canvas(
            self, height=220, bg=self.palette["card_alt"],
            highlightthickness=0, bd=0, cursor="sb_h_double_arrow",
        )
        self.canvas.pack(fill="both", expand=True, pady=(10, 0))
        self.canvas.bind("<Configure>", lambda _e: self._redraw())
        self.canvas.bind("<Button-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)

        # Data
        self._util_history: list[float] = []
        self._frag_history: list[float] = []
        self._event_types: list[str] = []  # "allocated", "failed", etc.
        self._current: int = -1
        self._dragging: bool = False
        self._last_jump: int = -1

    # ------------------------------------------------------------------
    def _legend_chip(self, parent, colour: str, text: str, pad=(0, 0)):
        wrap = ttk.Frame(parent, style="Card.TFrame")
        wrap.pack(side="left", padx=pad)
        dot = tk.Canvas(
            wrap, width=12, height=12,
            bg=self.palette["card"], highlightthickness=0, bd=0,
        )
        dot.create_oval(1, 1, 11, 11, fill=colour, outline=colour)
        dot.pack(side="left")
        ttk.Label(wrap, text=text, style="Muted.TLabel",
                  font=(self.palette.get("font_ui", "Segoe UI"), 10)
                  ).pack(side="left", padx=(5, 0))

    # ------------------------------------------------------------------
    def update_history(
        self,
        utilization: Iterable[float],
        fragmentation: Iterable[float],
        *,
        event_types: Optional[Iterable[str]] = None,
        current: int = -1,
    ) -> None:
        self._util_history = list(utilization)
        self._frag_history = list(fragmentation)
        self._event_types = list(event_types) if event_types else []
        self._current = current
        self.canvas.configure(bg=self.palette["card_alt"])
        self._redraw()

    def reset(self) -> None:
        self._util_history = []
        self._frag_history = []
        self._event_types = []
        self._current = -1
        self.canvas.configure(bg=self.palette["card_alt"])
        self._redraw()

    def apply_palette(self, palette: dict) -> None:
        self.palette = palette
        self.canvas.configure(bg=self.palette["card_alt"])
        self._redraw()

    # ------------------------------------------------------------------
    def _redraw(self) -> None:
        c = self.canvas
        c.delete("all")

        width, height, plot_left, plot_right, plot_top, plot_bottom = (
            self._plot_geometry()
        )
        plot_h = plot_bottom - plot_top

        # ---- Y axis grid + labels ----------------------------------
        for pct in (0, 25, 50, 75, 100):
            y = plot_bottom - (pct / 100) * plot_h
            c.create_line(
                plot_left, y, plot_right, y,
                fill=self.palette["border"],
                dash=(2, 4) if pct not in (0, 100) else None,
                width=1,
            )
            c.create_text(
                plot_left - 6, y, anchor="e",
                text=f"{pct}%",
                fill=self.palette["muted"],
                font=(self.palette.get("font_mono", "Consolas"), 10),
            )

        # Baseline tick at the very left for y=0
        c.create_line(plot_left, plot_top, plot_left, plot_bottom,
                      fill=self.palette["border"], width=1)

        # ---- empty state -------------------------------------------
        if not self._util_history:
            c.create_text(
                (plot_left + plot_right) / 2, height / 2,
                text="Run an allocation to see the history",
                fill=self.palette["muted"],
                font=(self.palette.get("font_ui", "Segoe UI"), 12, "italic"),
            )
            return

        n = len(self._util_history)

        def x_for(i: int) -> float:
            if n == 1:
                return (plot_left + plot_right) / 2
            return plot_left + (plot_right - plot_left) * (i / (n - 1))

        def y_for(value: float) -> float:
            v = max(0.0, min(100.0, value))
            return plot_bottom - (v / 100) * plot_h

        # ---- Utilization area + line -------------------------------
        util_pts: list[float] = []
        for i, v in enumerate(self._util_history):
            util_pts.extend([x_for(i), y_for(v)])

        if len(util_pts) >= 2:
            # Soft blended fill - 20% primary over card_alt.
            fill_colour = _blend(
                self.palette["primary"], self.palette["card_alt"], 0.22,
            )
            poly = util_pts + [plot_right, plot_bottom, plot_left, plot_bottom]
            c.create_polygon(poly, fill=fill_colour, outline="", smooth=True)

            # Crisp primary-coloured top line.
            c.create_line(
                util_pts, fill=self.palette["primary"],
                width=2, smooth=True,
                capstyle="round", joinstyle="round",
            )

        # ---- Fragmentation line ------------------------------------
        frag_pts: list[float] = []
        for i, v in enumerate(self._frag_history):
            frag_pts.extend([x_for(i), y_for(v)])
        if len(frag_pts) >= 2:
            c.create_line(
                frag_pts, fill=self.palette["warning"],
                width=2, smooth=True, dash=(4, 3),
                capstyle="round", joinstyle="round",
            )

        # ---- Event dots on utilization line ------------------------
        for i, ev in enumerate(self._event_types):
            if ev == "allocated":
                colour, outline = self.palette["success"], "#064e3b"
            elif ev == "failed":
                colour, outline = self.palette["danger"], "#7f1d1d"
            else:
                continue
            x, y = x_for(i), y_for(self._util_history[i])
            c.create_oval(
                x - 3, y - 3, x + 3, y + 3,
                fill=colour, outline=outline, width=1,
            )

        # ---- Current-step indicator --------------------------------
        if 0 <= self._current < n:
            cx = x_for(self._current)
            c.create_line(
                cx, plot_top, cx, plot_bottom,
                fill=self.palette["foreground"], width=1, dash=(3, 3),
            )
            # marker dots at the indicator
            c.create_oval(
                cx - 4, y_for(self._util_history[self._current]) - 4,
                cx + 4, y_for(self._util_history[self._current]) + 4,
                fill=self.palette["primary"], outline=self.palette["foreground"],
                width=2,
            )
            c.create_oval(
                cx - 4, y_for(self._frag_history[self._current]) - 4,
                cx + 4, y_for(self._frag_history[self._current]) + 4,
                fill=self.palette["warning"], outline=self.palette["foreground"],
                width=2,
            )

        # ---- Value chips on the right ------------------------------
        idx = self._current if 0 <= self._current < n else n - 1
        cur_util = self._util_history[idx]
        cur_frag = self._frag_history[idx]

        chip_x = plot_right + 12
        chip_w = width - chip_x - 4
        self._value_chip(
            chip_x, plot_top + 4, chip_w, 34,
            self.palette["primary"], f"{cur_util:.1f}%", "UTIL",
        )
        self._value_chip(
            chip_x, plot_top + 46, chip_w, 34,
            self.palette["warning"], f"{cur_frag:.1f}%", "FRAG",
        )

        # ---- X axis step label -------------------------------------
        c.create_text(
            plot_left, plot_bottom + 5, anchor="nw",
            text="step 1", fill=self.palette["muted"],
            font=(self.palette.get("font_mono", "Consolas"), 10),
        )
        c.create_text(
            plot_right, plot_bottom + 5, anchor="ne",
            text=f"step {n}", fill=self.palette["muted"],
            font=(self.palette.get("font_mono", "Consolas"), 10),
        )
        if 0 <= self._current < n:
            c.create_text(
                x_for(self._current), plot_bottom + 5, anchor="n",
                text=f"\u25b2 {self._current + 1}",
                fill=self.palette["foreground"],
                font=(self.palette.get("font_mono", "Consolas"), 10, "bold"),
            )

    # ------------------------------------------------------------------
    def _value_chip(self, x, y, w, h, colour, value_text, caption):
        c = self.canvas
        bg = _blend(colour, self.palette["card_alt"], 0.15)
        c.create_rectangle(
            x, y, x + w, y + h,
            fill=bg, outline=colour, width=1,
        )
        c.create_text(
            x + 8, y + h / 2 - 5, anchor="w",
            text=value_text,
            fill=colour,
            font=(self.palette.get("font_mono", "Consolas"), 13, "bold"),
        )
        c.create_text(
            x + w - 8, y + h / 2 + 6, anchor="e",
            text=caption,
            fill=self.palette["muted"],
            font=(self.palette.get("font_mono", "Consolas"), 10),
        )

    def _plot_geometry(self) -> tuple[int, int, int, int, int, int]:
        width = max(self.canvas.winfo_width(), 300)
        height = int(self.canvas["height"])
        plot_left = self.AXIS_W
        plot_right = max(plot_left + 40, width - self.RIGHT_W)
        plot_top = self.TOP_PAD
        plot_bottom = height - self.BOTTOM_PAD
        return width, height, plot_left, plot_right, plot_top, plot_bottom

    def _step_for_x(self, x_pos: int) -> Optional[int]:
        if not self._util_history:
            return None
        _, _, plot_left, plot_right, _, _ = self._plot_geometry()
        n = len(self._util_history)
        if n == 1:
            return 0
        x = max(plot_left, min(plot_right, x_pos))
        ratio = (x - plot_left) / max(1, plot_right - plot_left)
        return max(0, min(n - 1, int(round(ratio * (n - 1)))))

    def _jump_from_x(self, x_pos: int) -> None:
        if self._on_jump is None:
            return
        step = self._step_for_x(x_pos)
        if step is None or step == self._last_jump:
            return
        self._last_jump = step
        self._on_jump(step)

    def _on_press(self, event) -> None:
        self._dragging = True
        self._last_jump = -1
        self._jump_from_x(event.x)

    def _on_drag(self, event) -> None:
        if self._dragging:
            self._jump_from_x(event.x)

    def _on_release(self, event) -> None:
        if self._dragging:
            self._jump_from_x(event.x)
        self._dragging = False
        self._last_jump = -1
