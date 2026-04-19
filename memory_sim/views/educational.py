"""Educational section - algorithm explanations.

Mirrors ``OS-Project/src/components/simulator/EducationalSection.jsx``.
Content summarises PDF Section 2.3.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


ALGO_NOTES = [
    ("First Fit",
     "Scan the hole list from the beginning; take the first hole "
     "big enough. Fast, but fragments the low addresses."),
    ("Best Fit",
     "Scan all holes, pick the smallest that still fits. "
     "Minimises leftover waste per allocation but requires a full scan."),
    ("Worst Fit",
     "Pick the largest hole, hoping the leftover is big enough to be "
     "useful. Tends to deplete large holes quickly."),
    ("Next Fit",
     "First-Fit variant that continues searching from the last "
     "allocation, wrapping around. Spreads allocations more uniformly."),
]


class EducationalSection(ttk.Frame):
    def __init__(self, parent, *, palette: dict, **kwargs) -> None:
        super().__init__(parent, style="Card.TFrame", padding=12, **kwargs)
        self.palette = palette
        self._build()

    def _build(self) -> None:
        ttk.Label(self, text="ALGORITHMS",
                  style="SectionTitle.TLabel").pack(anchor="w")
        self._desc_labels: list[tk.Label] = []
        self._blocks: list[ttk.Frame] = []
        self.bind("<Configure>", self._on_resize)
        for name, desc in ALGO_NOTES:
            block = ttk.Frame(self, style="Card.TFrame")
            block.pack(fill="x", pady=(8, 0))
            self._blocks.append(block)
            ttk.Label(block, text=name,
                      style="Card.TLabel",
                      font=("Segoe UI", 11, "bold")).pack(anchor="w")
            lbl = tk.Label(
                block, text=desc, justify="left", anchor="w",
                bg=self.palette["card"], fg=self.palette["muted"],
                wraplength=220, font=("Segoe UI", 11),
            )
            lbl.pack(fill="x")
            self._desc_labels.append(lbl)

    def _on_resize(self, _event) -> None:
        wrap = max(260, self.winfo_width() - 36)
        for lbl in self._desc_labels:
            lbl.configure(wraplength=wrap)

    def apply_palette(self, palette: dict) -> None:
        self.palette = palette
        for lbl in self._desc_labels:
            lbl.configure(bg=self.palette["card"], fg=self.palette["muted"])
