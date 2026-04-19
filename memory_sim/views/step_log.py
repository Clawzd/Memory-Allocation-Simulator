"""Step log widget.

Mirrors ``OS-Project/src/components/simulator/StepLog.jsx``.
Clicking a line jumps to that step.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable


class StepLog(ttk.Frame):
    def __init__(
        self,
        parent,
        *,
        palette: dict,
        on_jump: Callable[[int], None],
        **kwargs,
    ) -> None:
        super().__init__(parent, style="Card.TFrame", padding=12, **kwargs)
        self.palette = palette
        self._on_jump = on_jump

        ttk.Label(self, text="STEP LOG",
                  style="SectionTitle.TLabel").pack(anchor="w")

        wrap = tk.Frame(self, bg=palette["card"])
        wrap.pack(fill="both", expand=True, pady=(8, 0))

        self.text = tk.Text(
            wrap, height=9, bd=0, wrap="word",
            bg=palette["card_alt"], fg=palette["foreground"],
            insertbackground=palette["foreground"],
            font=("Consolas", 12),
            padx=8, pady=6, cursor="hand2",
        )
        self.text.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(wrap, orient="vertical", command=self.text.yview)
        sb.pack(side="right", fill="y")
        self.text.configure(yscrollcommand=sb.set, state="disabled")

        self.text.tag_configure(
            "current", background=palette["primary"], foreground="#ffffff"
        )
        self.text.tag_configure("scanning", foreground=palette["warning"])
        self.text.tag_configure("allocated", foreground=palette["success"])
        self.text.tag_configure("deallocated", foreground=palette["warning"])
        self.text.tag_configure("failed", foreground=palette["danger"])
        self.text.tag_configure("considering", foreground=palette["accent"])
        self.text.tag_configure("initial", foreground=palette["muted"])
        self.text.tag_configure("done", foreground=palette["muted"])

        self.text.bind("<Button-1>", self._handle_click)

        self._steps: list[dict] = []

    # ------------------------------------------------------------------
    def set_steps(self, steps: list[dict], current: int) -> None:
        self._steps = steps
        self.text.configure(state="normal")
        self.text.delete("1.0", tk.END)
        for i, s in enumerate(steps):
            line_tag = s.get("type", "initial")
            self.text.insert(tk.END, f"{i+1:>3}. {s['message']}\n", line_tag)
        self._highlight(current)
        self.text.configure(state="disabled")
        self.text.see(f"{max(1, current + 1)}.0")

    def _highlight(self, current: int) -> None:
        self.text.tag_remove("current", "1.0", tk.END)
        if 0 <= current < len(self._steps):
            self.text.tag_add(
                "current",
                f"{current + 1}.0",
                f"{current + 1}.end",
            )

    def _handle_click(self, event) -> None:
        if not self._steps:
            return
        index = self.text.index(f"@{event.x},{event.y}")
        try:
            line = int(index.split(".")[0]) - 1
        except (ValueError, IndexError):
            return
        if 0 <= line < len(self._steps):
            self._on_jump(line)
