"""Ctrl+K command palette.

A modal search dialog listing every action with its keyboard shortcut.
Type to filter, Enter to execute, Escape to close.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable


Action = tuple[str, str, Callable[[], None]]  # (label, shortcut, fn)


class CommandPalette(tk.Toplevel):
    def __init__(self, parent, *, palette: dict, actions: list[Action]) -> None:
        super().__init__(parent)
        self.palette = palette
        self.withdraw()  # configure before showing
        self.title("Command Palette")
        self.transient(parent)
        self.overrideredirect(True)
        self.configure(bg=palette["card"])
        self._actions = actions
        self._filtered: list[Action] = list(actions)
        self._selected: int = 0

        outer = tk.Frame(
            self, bg=palette["card"],
            highlightthickness=1,
            highlightbackground=palette["primary"],
        )
        outer.pack(fill="both", expand=True)

        self._query = tk.StringVar()
        entry = tk.Entry(
            outer, textvariable=self._query,
            bg=palette["card"], fg=palette["foreground"],
            insertbackground=palette["foreground"],
            bd=0, relief="flat", font=("Segoe UI", 12),
        )
        entry.pack(fill="x", padx=14, pady=(10, 6))
        entry.focus_set()

        ttk.Separator(outer).pack(fill="x", padx=8)

        self.list_frame = tk.Frame(outer, bg=palette["card"])
        self.list_frame.pack(fill="both", expand=True, padx=6, pady=6)

        hint = tk.Label(
            outer,
            text="\u2191 \u2193 navigate  \u00b7  Enter run  \u00b7  Esc close",
            bg=palette["card"], fg=palette["muted"],
            font=("Segoe UI", 8),
        )
        hint.pack(anchor="e", padx=12, pady=(0, 8))

        self._row_widgets: list[tk.Frame] = []

        self._query.trace_add("write", lambda *_: self._filter())
        self.bind("<Escape>", lambda _e: self.destroy())
        self.bind("<Return>", lambda _e: self._execute_selected())
        self.bind("<Down>", lambda _e: self._move(+1))
        self.bind("<Up>", lambda _e: self._move(-1))
        self.bind("<FocusOut>", lambda _e: self.destroy())

        self._render()
        self._center_on_parent(parent)
        self.deiconify()
        self.grab_set()

    # ------------------------------------------------------------------
    def _center_on_parent(self, parent) -> None:
        parent.update_idletasks()
        self.update_idletasks()
        w = 520
        h = 44 + min(9, max(1, len(self._actions))) * 30 + 50
        px = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
        py = parent.winfo_rooty() + 80
        self.geometry(f"{w}x{h}+{px}+{py}")

    # ------------------------------------------------------------------
    def _filter(self) -> None:
        q = self._query.get().strip().lower()
        if not q:
            self._filtered = list(self._actions)
        else:
            self._filtered = [
                a for a in self._actions if q in a[0].lower() or q in a[1].lower()
            ]
        self._selected = 0
        self._render()

    def _move(self, delta: int) -> None:
        if not self._filtered:
            return
        self._selected = (self._selected + delta) % len(self._filtered)
        self._render()

    def _execute_selected(self) -> None:
        if not self._filtered:
            return
        action = self._filtered[self._selected]
        self.destroy()
        action[2]()

    def _render(self) -> None:
        for w in self._row_widgets:
            w.destroy()
        self._row_widgets.clear()

        for i, (label, shortcut, _fn) in enumerate(self._filtered):
            bg = self.palette["primary"] if i == self._selected else self.palette["card"]
            fg = "#ffffff" if i == self._selected else self.palette["foreground"]
            sub_fg = "#e5e7eb" if i == self._selected else self.palette["muted"]

            row = tk.Frame(self.list_frame, bg=bg, cursor="hand2")
            row.pack(fill="x", pady=1)
            tk.Label(
                row, text=label, bg=bg, fg=fg,
                font=("Segoe UI", 10), anchor="w",
            ).pack(side="left", padx=10, pady=6)
            if shortcut:
                tk.Label(
                    row, text=shortcut, bg=bg, fg=sub_fg,
                    font=("Consolas", 9),
                ).pack(side="right", padx=10)

            def _bind(row=row, idx=i):
                row.bind("<Button-1>",
                         lambda _e: (setattr(self, "_selected", idx),
                                     self._execute_selected()))
                row.bind("<Enter>",
                         lambda _e: (setattr(self, "_selected", idx),
                                     self._render()))
            _bind()
            self._row_widgets.append(row)

        if not self._filtered:
            empty = tk.Label(
                self.list_frame,
                text="No matching actions",
                bg=self.palette["card"], fg=self.palette["muted"],
                font=("Segoe UI", 10, "italic"), pady=16,
            )
            empty.pack()
            self._row_widgets.append(empty)
