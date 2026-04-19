"""Right panel: pro dashboard-style statistics + process table.

Designed to feel like a real analytics panel:

  * Hero **donut** showing utilization at a glance.
  * Two-stop **memory bar** showing Used vs. Free as one stacked bar.
  * **Fragmentation bar** colour-coded against utilization so the user
    can spot at a glance when memory is fragmented.
  * Compact **fact grid** (Total / Holes / Largest hole).
  * **Process table** below, unchanged.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..theme import color_for_process


# ----------------------------- colour helpers ------------------------------


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _rgb_to_hex(rgb):
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(c))) for c in rgb)


def _blend(fg: str, bg: str, alpha: float) -> str:
    fr, fg_, fb = _hex_to_rgb(fg)
    br, bg_, bb = _hex_to_rgb(bg)
    return _rgb_to_hex((
        fr * alpha + br * (1 - alpha),
        fg_ * alpha + bg_ * (1 - alpha),
        fb * alpha + bb * (1 - alpha),
    ))


# ---------------------------------------------------------------------------
# Donut utilisation widget
# ---------------------------------------------------------------------------


class _Donut(tk.Canvas):
    """Canvas-based circular progress donut with a label in the middle."""

    SIZE = 124
    THICK = 9

    def __init__(self, parent, palette: dict) -> None:
        super().__init__(
            parent, width=self.SIZE, height=self.SIZE,
            bg=palette["card"], highlightthickness=0, bd=0,
        )
        self.palette = palette
        self._percent = 0.0
        self._caption = ""
        self._redraw()

    def set_value(self, percent: float, caption: str = "") -> None:
        self._percent = max(0.0, min(100.0, percent))
        self._caption = caption
        self._redraw()

    def apply_palette(self, palette: dict) -> None:
        self.palette = palette
        self.configure(bg=palette["card"])
        self._redraw()

    def _redraw(self) -> None:
        self.delete("all")
        s = self.SIZE
        t = self.THICK
        pad = 6
        bbox = (pad, pad, s - pad, s - pad)

        # Track: draw as two filled ovals. Tk's thick arc outlines look jagged
        # at this size, while filled ovals render noticeably smoother.
        track = _blend(self.palette["border"], self.palette["card"], 0.7)
        self.create_oval(bbox, fill=track, outline=track, width=0)
        inner = (pad + t, pad + t, s - pad - t, s - pad - t)
        self.create_oval(
            inner,
            fill=self.palette["card"],
            outline=self.palette["card"],
            width=0,
        )
        # Progress arc - start at 12 o'clock, go clockwise.
        if self._percent > 0:
            extent = -self._percent * 3.6   # clockwise
            self.create_arc(
                bbox, start=90, extent=extent,
                style="arc", outline=self.palette["primary"], width=t,
            )

        # Center text - big percent + caption
        mx, my = s / 2, s / 2
        self.create_text(
            mx, my - 6,
            text=f"{self._percent:.1f}%",
            fill=self.palette["foreground"],
            font=(self.palette.get("font_ui", "Segoe UI"), 18, "bold"),
        )
        self.create_text(
            mx, my + 14,
            text=self._caption or "utilization",
            fill=self.palette["muted"],
            font=(self.palette.get("font_ui", "Segoe UI"), 9),
        )


# ---------------------------------------------------------------------------
# Main panel
# ---------------------------------------------------------------------------


class StatsPanel(ttk.Frame):
    def __init__(self, parent, *, palette: dict, **kwargs) -> None:
        super().__init__(parent, style="Card.TFrame", padding=14, **kwargs)
        self.palette = palette
        self._build()

    def _build(self) -> None:
        ttk.Label(self, text="STATISTICS",
                  style="SectionTitle.TLabel").pack(anchor="w")

        # --- hero donut ---------------------------------------------------
        donut_row = tk.Frame(self, bg=self.palette["card"], bd=0, highlightthickness=0)
        self._donut_row = donut_row
        donut_row.pack(fill="x", pady=(10, 6))
        self.donut = _Donut(donut_row, self.palette)
        self.donut.pack(anchor="center")

        # --- memory bar ---------------------------------------------------
        ttk.Label(self, text="MEMORY",
                  style="SectionTitle.TLabel").pack(anchor="w", pady=(6, 4))
        self.mem_bar = tk.Canvas(
            self, height=22, bg=self.palette["card_alt"],
            highlightthickness=0, bd=0,
        )
        self.mem_bar.pack(fill="x")
        self.mem_bar.bind("<Configure>", lambda _e: self._draw_mem_bar())

        mem_labels = ttk.Frame(self, style="Card.TFrame")
        mem_labels.pack(fill="x", pady=(4, 6))
        self.used_var = tk.StringVar(value="Used - KB")
        self.free_var = tk.StringVar(value="Free - KB")
        ttk.Label(mem_labels, textvariable=self.used_var,
                  style="Card.TLabel",
                  font=(self.palette.get("font_mono", "Consolas"), 11, "bold"),
                  foreground=self.palette["primary"]
                  ).pack(side="left")
        ttk.Label(mem_labels, textvariable=self.free_var,
                  style="Muted.TLabel",
                  font=(self.palette.get("font_mono", "Consolas"), 11)
                  ).pack(side="right")

        # --- fragmentation bar -------------------------------------------
        ttk.Label(self, text="EXTERNAL FRAGMENTATION",
                  style="SectionTitle.TLabel").pack(anchor="w", pady=(8, 4))
        self.frag_bar = tk.Canvas(
            self, height=18, bg=self.palette["card_alt"],
            highlightthickness=0, bd=0,
        )
        self.frag_bar.pack(fill="x")
        self.frag_bar.bind("<Configure>", lambda _e: self._draw_frag_bar())

        frag_row = ttk.Frame(self, style="Card.TFrame")
        frag_row.pack(fill="x", pady=(4, 6))
        self.frag_var = tk.StringVar(value="0.0%")
        self.frag_desc_var = tk.StringVar(value="memory is contiguous")
        ttk.Label(frag_row, textvariable=self.frag_var,
                  style="Card.TLabel",
                  font=(self.palette.get("font_mono", "Consolas"), 11, "bold"),
                  foreground=self.palette["warning"]
                  ).pack(side="left")
        ttk.Label(frag_row, textvariable=self.frag_desc_var,
                  style="Muted.TLabel",
                  font=(self.palette.get("font_ui", "Segoe UI"), 11)
                  ).pack(side="right")

        # --- fact grid ----------------------------------------------------
        facts = ttk.Frame(self, style="Card.TFrame")
        facts.pack(fill="x", pady=(10, 4))
        self._fact_cells: dict[str, tk.StringVar] = {}
        self._fact_widgets: list[tuple[tk.Frame, tk.Label, tk.Label]] = []
        for i, (key, label) in enumerate([
            ("total",        "Total"),
            ("num_holes",    "Holes"),
            ("largest_free", "Largest Hole"),
            ("process_count", "Processes"),
        ]):
            cell = tk.Frame(
                facts, bg=self.palette["card_alt"],
                highlightthickness=1,
                highlightbackground=self.palette["card"],
            )
            row, col = divmod(i, 2)
            cell.grid(row=row, column=col, sticky="ew", padx=(0, 4 if col == 0 else 0),
                      pady=(0, 4))
            facts.columnconfigure(col, weight=1)
            label_widget = tk.Label(cell, text=label,
                                    bg=self.palette["card_alt"],
                                    fg=self.palette["muted"],
                                    font=(self.palette.get("font_ui", "Segoe UI"), 10),
                                    anchor="w")
            label_widget.pack(anchor="w", padx=8, pady=(6, 0))
            var = tk.StringVar(value="-")
            self._fact_cells[key] = var
            value_widget = tk.Label(cell, textvariable=var,
                                    bg=self.palette["card_alt"],
                                    fg=self.palette["foreground"],
                                    font=(self.palette.get("font_mono", "Consolas"), 13, "bold"),
                                    anchor="w")
            value_widget.pack(anchor="w", padx=8, pady=(0, 6))
            self._fact_widgets.append((cell, label_widget, value_widget))

        # --- process table ------------------------------------------------
        ttk.Label(self, text="PROCESSES",
                  style="SectionTitle.TLabel").pack(anchor="w", pady=(8, 4))
        table_wrap = tk.Frame(self, bg=self.palette["card"])
        self._table_wrap = table_wrap
        table_wrap.pack(fill="both", expand=True)
        columns = ("name", "size", "start", "end")
        self.tree = ttk.Treeview(
            table_wrap, columns=columns, show="headings", height=8,
            style="Treeview",
        )
        for col, text, w in [
            ("name", "Name", 95),
            ("size", "Size", 80),
            ("start", "Start", 80),
            ("end", "End", 80),
        ]:
            self.tree.heading(col, text=text)
            self.tree.column(col, width=w, anchor="center")
        self.tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(table_wrap, orient="vertical",
                           command=self.tree.yview)
        sb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=sb.set)

        # current state cache for re-draw on resize
        self._last_used = 0
        self._last_total = 1
        self._last_frag = 0.0

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------
    def update_state(self, blocks: list[dict], stats: dict) -> None:
        self.mem_bar.configure(bg=self.palette["card_alt"])
        self.frag_bar.configure(bg=self.palette["card_alt"])
        self.donut.apply_palette(self.palette)
        self._last_used = stats["used"]
        self._last_total = stats["total"]
        self._last_frag = stats["external_fragmentation"]

        # Donut
        self.donut.set_value(stats["utilization"], "utilization")

        # Memory labels
        self.used_var.set(
            f"Used  {stats['used']} KB  ({stats['used_percent']}%)"
        )
        self.free_var.set(
            f"Free  {stats['free']} KB  ({stats['free_percent']}%)"
        )

        # Fragmentation labels
        frag = stats["external_fragmentation"]
        self.frag_var.set(f"{frag:.1f}%")
        if frag < 1:
            desc = "memory is contiguous"
        elif frag < 25:
            desc = "lightly fragmented"
        elif frag < 50:
            desc = "moderately fragmented"
        elif frag < 75:
            desc = "heavily fragmented"
        else:
            desc = "severely fragmented"
        self.frag_desc_var.set(desc)

        # Fact grid
        self._fact_cells["total"].set(f"{stats['total']} KB")
        self._fact_cells["num_holes"].set(str(stats["num_holes"]))
        self._fact_cells["largest_free"].set(f"{stats['largest_free']} KB")
        self._fact_cells["process_count"].set(str(stats["process_count"]))

        # Redraw bars at whatever size they are now.
        self._draw_mem_bar()
        self._draw_frag_bar(blocks)

        # Process table
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        for b in blocks:
            if b["is_free"]:
                continue
            tag = f"c{b.get('color_index', 0) % 8}"
            self.tree.insert(
                "", "end",
                values=(b["name"], b["size"], b["start"], b["end"]),
                tags=(tag,),
            )
        for i in range(8):
            self.tree.tag_configure(f"c{i}", foreground=color_for_process(i))

    def apply_palette(self, palette: dict) -> None:
        self.palette = palette
        self.donut.apply_palette(palette)
        if hasattr(self, "_donut_row"):
            self._donut_row.configure(bg=palette["card"])
        self.mem_bar.configure(bg=palette["card_alt"])
        self.frag_bar.configure(bg=palette["card_alt"])
        if hasattr(self, "_table_wrap"):
            self._table_wrap.configure(bg=palette["card"])
        for cell, label_widget, value_widget in self._fact_widgets:
            cell.configure(
                bg=palette["card_alt"],
                highlightbackground=palette["card"],
            )
            label_widget.configure(
                bg=palette["card_alt"],
                fg=palette["muted"],
            )
            value_widget.configure(
                bg=palette["card_alt"],
                fg=palette["foreground"],
            )
        self._draw_mem_bar()
        self._draw_frag_bar()

    # ------------------------------------------------------------------
    # Bar drawings
    # ------------------------------------------------------------------
    def _draw_mem_bar(self, blocks: list[dict] | None = None) -> None:
        c = self.mem_bar
        c.delete("all")
        w = max(c.winfo_width(), 40)
        h = int(c["height"])
        used = self._last_used
        total = max(1, self._last_total)

        # Rounded background track.
        self._rounded_rect(c, 0, 0, w, h, r=h / 2,
                           fill=self.palette["card_alt"],
                           outline=self.palette["border"], width=1)

        if used > 0:
            used_w = max(h, int(w * used / total))
            self._rounded_rect(c, 0, 0, used_w, h, r=h / 2,
                               fill=self.palette["primary"],
                               outline=self.palette["primary"], width=1)

        # Subtle free-section hatching via a single light-shaded strip is
        # unnecessary; the end of the bar speaks for itself.

    def _draw_frag_bar(self, blocks: list[dict] | None = None) -> None:
        c = self.frag_bar
        c.delete("all")
        w = max(c.winfo_width(), 40)
        h = int(c["height"])
        frag = self._last_frag

        # Background track
        self._rounded_rect(c, 0, 0, w, h, r=h / 2,
                           fill=self.palette["card_alt"],
                           outline=self.palette["border"], width=1)

        # Gradient-ish: warning shade interpolates to danger as frag rises.
        if frag > 0:
            if frag < 50:
                colour = self.palette["warning"]
            else:
                # interpolate warning -> danger for 50-100%
                t = (frag - 50) / 50
                colour = _blend(self.palette["danger"],
                                self.palette["warning"], t)
            filled_w = max(h, int(w * frag / 100))
            self._rounded_rect(c, 0, 0, filled_w, h, r=h / 2,
                               fill=colour, outline=colour, width=1)

        # Tick marks at 25 / 50 / 75 %
        for pct in (25, 50, 75):
            x = int(w * pct / 100)
            c.create_line(x, 2, x, h - 2,
                          fill=self.palette["border"], width=1, dash=(1, 2))

    # ------------------------------------------------------------------
    @staticmethod
    def _rounded_rect(canvas, x1, y1, x2, y2, r=6, **kw):
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
        return canvas.create_polygon(points, smooth=True, splinesteps=18, **kw)
