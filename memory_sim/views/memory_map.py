"""Center-top panel: animated, rounded, gradient-shaded memory map.

Far beyond the React web version: blocks are drawn as rounded polygons
with a top highlight + bottom shadow line for depth, transitions between
simulation steps are smoothly interpolated with an easing curve, and an
address ruler with tick marks sits below the bar. Hover dims every
other block so the inspected one stands out.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from ..theme import FIT_OUTLINE, SCAN_OUTLINE, color_for_process


# ---------------------------------------------------------------------------
# Small colour helpers (no external deps)
# ---------------------------------------------------------------------------


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(c))) for c in rgb)


def _shade(hex_color: str, factor: float) -> str:
    """Lighten (factor > 1) or darken (factor < 1) a hex colour."""
    r, g, b = _hex_to_rgb(hex_color)
    return _rgb_to_hex((r * factor, g * factor, b * factor))


def _ease_out_cubic(t: float) -> float:
    return 1 - (1 - t) ** 3


# ---------------------------------------------------------------------------
# Widget
# ---------------------------------------------------------------------------


ANIM_FRAMES = 14
ANIM_INTERVAL_MS = 16


class MemoryMap(ttk.Frame):
    def __init__(
        self,
        parent,
        *,
        palette: dict,
        on_deallocate: Optional[Callable[[str], None]] = None,
        **kwargs,
    ) -> None:
        super().__init__(parent, style="Card.TFrame", padding=16, **kwargs)
        self.palette = palette
        self._on_deallocate = on_deallocate

        # current (target) state
        self._blocks: list[dict] = []
        self._total: int = 1
        self._scan_id: Optional[str] = None
        self._fit_id: Optional[str] = None
        # last rendered state (for animation source)
        self._prev_blocks_by_id: dict[str, dict] = {}
        self._hover_id: Optional[str] = None
        self._anim_after: Optional[str] = None
        self._anim_frame: int = ANIM_FRAMES  # start at end
        self._rect_items: dict[int, dict] = {}
        self._tooltip: Optional[tk.Toplevel] = None

        self._build()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def _build(self) -> None:
        header = ttk.Frame(self, style="Card.TFrame")
        header.pack(fill="x")
        ttk.Label(header, text="MEMORY MAP",
                  style="SectionTitle.TLabel").pack(side="left")
        sub = ttk.Label(
            header,
            text="hover for details  \u00b7  right-click to free",
            style="Muted.TLabel",
        )
        sub.pack(side="left", padx=(10, 0))

        self.badge_var = tk.StringVar(value="")
        self.badge = ttk.Label(header, textvariable=self.badge_var,
                               style="Badge.TLabel")
        self.badge.pack(side="right")
        self.live_var = tk.StringVar(value="")
        self.live_badge = ttk.Label(header, textvariable=self.live_var,
                                    style="LiveBadge.TLabel")
        self.live_badge.pack(side="right", padx=(0, 6))

        self.canvas = tk.Canvas(
            self, height=220, bg=self.palette["canvas"],
            highlightthickness=0, bd=0,
        )
        self.canvas.pack(fill="both", expand=True, pady=(12, 4))
        self.canvas.bind("<Configure>", lambda _e: self._redraw())
        self.canvas.bind("<Motion>", self._on_motion)
        self.canvas.bind("<Leave>", self._on_leave)
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<Button-3>", self._on_right_click)

        self.meta_var = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.meta_var,
                  style="Muted.TLabel").pack(anchor="w", pady=(4, 0))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def set_state(
        self,
        blocks: list[dict],
        total: int,
        *,
        scan_id: Optional[str] = None,
        fit_id: Optional[str] = None,
        algorithm_label: str = "",
        live: bool = False,
        animate: bool = True,
    ) -> None:
        # snapshot previous positions BEFORE overwriting
        if animate and self._blocks:
            self._prev_blocks_by_id = {b["id"]: dict(b) for b in self._blocks}
        elif not animate:
            self._prev_blocks_by_id = {}

        self._blocks = blocks
        self._total = max(1, total)
        self._scan_id = scan_id
        self._fit_id = fit_id
        self.canvas.configure(bg=self.palette["canvas"])
        self.badge_var.set(algorithm_label)
        self.live_var.set("LIVE" if live else "")

        # start animation
        if self._anim_after is not None:
            try:
                self.after_cancel(self._anim_after)
            except Exception:
                pass
            self._anim_after = None
        self._anim_frame = 0 if animate and self._prev_blocks_by_id else ANIM_FRAMES
        self._step_animation()

    def apply_palette(self, palette: dict) -> None:
        self.palette = palette
        self.canvas.configure(bg=self.palette["canvas"])
        self._redraw()

    # ------------------------------------------------------------------
    # Animation driver
    # ------------------------------------------------------------------
    def _step_animation(self) -> None:
        self._redraw()
        if self._anim_frame < ANIM_FRAMES:
            self._anim_frame += 1
            self._anim_after = self.after(ANIM_INTERVAL_MS, self._step_animation)
        else:
            self._anim_after = None

    def _interp(self, prev: Optional[dict], curr: dict, key: str) -> float:
        """Ease between prev[key] and curr[key] using current animation frame."""
        if prev is None or self._anim_frame >= ANIM_FRAMES:
            return float(curr[key])
        t = _ease_out_cubic(self._anim_frame / ANIM_FRAMES)
        return prev[key] * (1 - t) + curr[key] * t

    # ------------------------------------------------------------------
    # Drawing primitives
    # ------------------------------------------------------------------
    def _rounded_rect(self, x1, y1, x2, y2, r=6, **kw):
        """Rounded rectangle via a smoothed polygon."""
        r = min(r, (x2 - x1) / 2, (y2 - y1) / 2)
        points = [
            x1 + r, y1,
            x2 - r, y1,
            x2, y1,
            x2, y1 + r,
            x2, y2 - r,
            x2, y2,
            x2 - r, y2,
            x1 + r, y2,
            x1, y2,
            x1, y2 - r,
            x1, y1 + r,
            x1, y1,
        ]
        return self.canvas.create_polygon(points, smooth=True, splinesteps=24, **kw)

    # ------------------------------------------------------------------
    # Main draw
    # ------------------------------------------------------------------
    def _redraw(self) -> None:
        self.canvas.delete("all")
        self._rect_items.clear()

        width = max(self.canvas.winfo_width(), 400)
        pad_x = 12
        inner_w = width - 2 * pad_x
        height = int(self.canvas["height"])
        bar_height = min(120, max(80, int(height * 0.34)))
        bar_top = max(18, int((height - bar_height) / 2) - 10)
        bar_bottom = bar_top + bar_height
        bar_height = bar_bottom - bar_top

        # ------ empty state ------
        if not self._blocks or self._total <= 0:
            self.canvas.create_text(
                width / 2, height / 2,
                text="Configure memory on the left, then click Run.",
                fill=self.palette["muted"], font=("Segoe UI", 11, "italic"),
            )
            self.meta_var.set("")
            return

        # ------ bar background ------
        self._rounded_rect(
            pad_x - 2, bar_top - 3, pad_x + inner_w + 2, bar_bottom + 3, r=10,
            fill=self.palette["card_alt"], outline=self.palette["card"],
            width=1,
        )

        # ------ each block ------
        # We lay blocks out by pixel starting at pad_x; during animation
        # each block's start/size is eased from the previous snapshot.
        cursor = float(pad_x)
        for b in self._blocks:
            prev = self._prev_blocks_by_id.get(b["id"])
            size_now = self._interp(prev, b, "size")
            bw = max(4.0, (size_now / self._total) * inner_w)

            # fade-in alpha for newly-appearing blocks: approximated by
            # blending block colour toward background.
            alpha = 1.0
            if prev is None and self._anim_frame < ANIM_FRAMES:
                alpha = _ease_out_cubic(self._anim_frame / ANIM_FRAMES)

            if b["is_free"]:
                base = self.palette.get("free", "#334155")
                text_fill = self.palette.get("free_text", self.palette["foreground"])
                label = f"{b['size']} free"
            else:
                base = color_for_process(b.get("color_index", 0))
                text_fill = "#ffffff"
                label = b.get("name") or "?"

            # blend toward canvas background for fade-in
            if alpha < 1.0:
                br, bg, bb = _hex_to_rgb(base)
                cr, cg, cb = _hex_to_rgb(self.palette["canvas"])
                base = _rgb_to_hex((
                    cr + (br - cr) * alpha,
                    cg + (bg - cg) * alpha,
                    cb + (bb - cb) * alpha,
                ))

            # Dim non-hovered blocks when hovering something.
            if self._hover_id is not None and self._hover_id != b["id"]:
                base = _shade(base, 0.65)

            outline = _shade(base, 0.75)
            outline_w = 1
            if b["id"] == self._fit_id:
                outline = FIT_OUTLINE
                outline_w = 3
            elif b["id"] == self._scan_id:
                outline = SCAN_OUTLINE
                outline_w = 3

            y1, y2 = bar_top, bar_bottom
            rect_id = self._rounded_rect(
                cursor, y1, cursor + bw, y2, r=6,
                fill=base, outline=outline, width=outline_w,
            )
            self._rect_items[rect_id] = b

            # Depth: thin highlight at top, thin shadow at bottom.
            if bw > 6:
                self.canvas.create_line(
                    cursor + 3, y1 + 2, cursor + bw - 3, y1 + 2,
                    fill=_shade(base, 1.35), width=1,
                )
                self.canvas.create_line(
                    cursor + 3, y2 - 2, cursor + bw - 3, y2 - 2,
                    fill=_shade(base, 0.65), width=1,
                )

            # Labels (process name big, size small).
            if bw > 50:
                self.canvas.create_text(
                    cursor + bw / 2, (y1 + y2) / 2 - 6,
                    text=label, fill=text_fill,
                    font=("Segoe UI", 13, "bold"),
                )
                self.canvas.create_text(
                    cursor + bw / 2, (y1 + y2) / 2 + 10,
                    text=f"{b['size']} KB",
                    fill=text_fill, font=("Segoe UI", 10),
                )
            elif bw > 24:
                self.canvas.create_text(
                    cursor + bw / 2, (y1 + y2) / 2,
                    text=label, fill=text_fill,
                    font=("Segoe UI", 10, "bold"),
                )

            # Address tick under each boundary (only if wide enough).
            if bw > 40:
                self.canvas.create_text(
                    cursor, bar_bottom + 6, anchor="n",
                    text=str(b["start"]),
                    fill=self.palette["muted"], font=("Consolas", 9),
                )

            cursor += bw

        # Ruler tail tick for total size
        self.canvas.create_text(
            pad_x + inner_w, bar_bottom + 6, anchor="ne",
            text=str(self._total),
            fill=self.palette["muted"], font=("Consolas", 9, "bold"),
        )

        # Meta line
        num_segments = len(self._blocks)
        procs = sum(1 for b in self._blocks if not b["is_free"])
        holes = num_segments - procs
        self.meta_var.set(
            f"{num_segments} segment(s)  \u00b7  {procs} process(es)  \u00b7  "
            f"{holes} hole(s)  \u00b7  address space 0 - {self._total - 1}"
        )

    # ------------------------------------------------------------------
    # Mouse interaction
    # ------------------------------------------------------------------
    def _block_under(self, x: int, y: int) -> Optional[dict]:
        items = self.canvas.find_overlapping(x, y, x, y)
        for item in items:
            if item in self._rect_items:
                return self._rect_items[item]
        return None

    def _on_motion(self, event) -> None:
        b = self._block_under(event.x, event.y)
        new_id = b["id"] if b else None
        if new_id != self._hover_id:
            self._hover_id = new_id
            self._redraw()
        if b is None:
            self._hide_tooltip()
            return
        if b["is_free"]:
            text = (
                "FREE HOLE\n"
                f"Size:   {b['size']} KB\n"
                f"Range:  {b['start']} \u2013 {b['end']}"
            )
        else:
            text = (
                f"PROCESS {b['name']}\n"
                f"Size:   {b['size']} KB\n"
                f"Range:  {b['start']} \u2013 {b['end']}\n"
                f"Right-click to free"
            )
        self._show_tooltip(event.x_root + 14, event.y_root + 16, text)

    def _on_leave(self, _event) -> None:
        if self._hover_id is not None:
            self._hover_id = None
            self._redraw()
        self._hide_tooltip()

    def _show_tooltip(self, x: int, y: int, text: str) -> None:
        if self._tooltip is None:
            tip = tk.Toplevel(self)
            tip.wm_overrideredirect(True)
            tip.configure(bg=self.palette["card"])
            outer = tk.Frame(
                tip, bg=self.palette["card"],
                highlightthickness=1,
                highlightbackground=self.palette["primary"],
            )
            outer.pack()
            lbl = tk.Label(
                outer, text=text, justify="left",
                bg=self.palette["card"], fg=self.palette["foreground"],
                font=("Consolas", 9), padx=10, pady=6,
            )
            lbl.pack()
            self._tooltip = tip
            self._tooltip_label = lbl
        else:
            self._tooltip_label.configure(text=text)
        self._tooltip.geometry(f"+{x}+{y}")
        self._tooltip.deiconify()

    def _hide_tooltip(self) -> None:
        if self._tooltip is not None:
            self._tooltip.withdraw()

    def _on_click(self, event) -> None:
        self._on_motion(event)

    def _on_right_click(self, event) -> None:
        if self._on_deallocate is None:
            return
        b = self._block_under(event.x, event.y)
        if b is None or b["is_free"]:
            return
        self._on_deallocate(b["name"])
