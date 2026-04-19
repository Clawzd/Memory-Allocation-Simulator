"""Comparison dialog: run all four algorithms on the same workload.

Mirrors ``OS-Project/src/components/simulator/ComparisonTable.jsx``.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class ComparisonDialog(tk.Toplevel):
    def __init__(self, parent, *, palette: dict, results: list[dict]) -> None:
        super().__init__(parent)
        self.palette = palette
        self.title("Algorithm Comparison")
        self.configure(bg=palette["background"])
        self.geometry("880x340")
        self.transient(parent)

        ttk.Label(self, text="ALGORITHM COMPARISON",
                  style="SectionTitle.TLabel",
                  background=palette["background"]).pack(anchor="w",
                                                         padx=16, pady=(12, 4))
        ttk.Label(
            self,
            text="Same workload run against every strategy. Lower "
                 "external fragmentation and higher utilization are better.",
            style="Muted.TLabel",
            background=palette["background"],
        ).pack(anchor="w", padx=16, pady=(0, 10))

        cols = (
            "label", "util", "used", "free", "holes", "largest",
            "scans", "avg_scan", "alloc", "failed",
        )
        tree = ttk.Treeview(self, columns=cols, show="headings", height=8)
        headers = {
            "label":   ("Algorithm",    110),
            "util":    ("Utilization",  90),
            "used":    ("Used",         70),
            "free":    ("Free",         70),
            "holes":   ("# Holes",      70),
            "largest": ("Largest Hole", 100),
            "scans":   ("Scanned",      80),
            "avg_scan":("Avg Scan",     80),
            "alloc":   ("Allocated",    80),
            "failed":  ("Failed",       70),
        }
        for col, (text, width) in headers.items():
            tree.heading(col, text=text)
            tree.column(col, width=width, anchor="center")

        for r in results:
            if "error" in r:
                tree.insert("", "end", values=(
                    r["label"], "ERROR", "-", "-", "-", "-", "-", "-", "-", r["error"],
                ))
                continue
            tree.insert("", "end", values=(
                r["label"],
                f"{r['utilization']}%",
                f"{r['used']}",
                f"{r['free']}",
                r["holes"],
                r["largest_free"],
                r["scanned_blocks"],
                r["avg_scan"],
                r["allocated_processes"],
                r["failed_processes"],
            ))
        tree.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        ttk.Button(self, text="Close", style="Primary.TButton",
                   command=self.destroy).pack(pady=(0, 14))
