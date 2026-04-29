"""Left panel: configuration + process management (PDF UI Section 1.4).

Mirrors the layout of ``OS-Project/src/components/simulator/InputPanel.jsx``
and provides every knob listed in the PDF User Interface Requirements:

* total memory size + unit selector (KB/MB)
* algorithm selector
* add/remove process form
* Run / Reset / Compare / Compact / Step-mode toggle
"""

from __future__ import annotations

import random
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable

from ..algorithms import ALGORITHMS, pretty_name
from ..model import unit_scale
from ..theme import color_for_process


class ControlPanel(ttk.Frame):
    def __init__(
        self,
        parent,
        *,
        palette: dict,
        on_run: Callable[[], None],
        on_reset: Callable[[], None],
        on_compare: Callable[[], None],
        on_compact: Callable[[], None],
        on_change: Callable[[], None],
        **kwargs,
    ) -> None:
        super().__init__(parent, style="Card.TFrame", padding=12, **kwargs)
        self.palette = palette
        self._on_run = on_run
        self._on_reset = on_reset
        self._on_compare = on_compare
        self._on_compact = on_compact
        self._on_change = on_change

        # Shared state variables -------------------------------------------------
        self.total_memory = tk.IntVar(value=512)
        self.unit = tk.StringVar(value="KB")        # KB / MB - PDF FR-01
        self.algorithm = tk.StringVar(value="first-fit")
        self.algorithm_label = tk.StringVar(value="")
        self.step_mode = tk.BooleanVar(value=True)  # PDF FR-09
        self.step_mode_label = tk.StringVar(value="")
        self.new_name = tk.StringVar(value="")
        self.new_size = tk.StringVar(value="")
        self._algo_labels = {key: pretty_name(key) for key in ALGORITHMS}
        self._algo_keys_by_label = {label: key for key, label in self._algo_labels.items()}

        # Start empty so users can build workload manually or use presets.
        self.processes: list[dict] = []

        self._build()
        self._refresh_process_list()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def _build(self) -> None:
        ttk.Label(self, text="CONFIGURATION", style="SectionTitle.TLabel").pack(
            anchor="w", pady=(0, 8)
        )

        # --- total memory ------------------------------------------------
        ttk.Label(self, text="Total Memory", style="Muted.TLabel").pack(anchor="w")
        mem_row = ttk.Frame(self, style="Card.TFrame")
        mem_row.pack(fill="x", pady=(2, 10))
        self.mem_entry = ttk.Entry(
            mem_row, textvariable=self.total_memory, width=10,
            font=("Segoe UI", 14),
        )
        self.mem_entry.pack(side="left", fill="x", expand=True)
        unit_combo = ttk.Combobox(
            mem_row, textvariable=self.unit,
            values=("KB", "MB"), state="readonly", width=4,
            font=("Segoe UI", 13),
        )
        unit_combo.pack(side="left", padx=(6, 0))
        unit_combo.bind("<<ComboboxSelected>>", lambda _e: self._on_change())
        self.mem_entry.bind("<FocusOut>", lambda _e: self._on_change())

        # --- algorithm ---------------------------------------------------
        ttk.Label(self, text="Algorithm", style="Muted.TLabel").pack(anchor="w")
        self._algo_combo = ttk.Combobox(
            self,
            textvariable=self.algorithm_label,
            values=tuple(self._algo_labels.values()),
            state="readonly",
            font=("Segoe UI", 14),
            postcommand=self._refresh_algorithm_choices,
        )
        self._algo_combo.pack(fill="x", pady=(2, 10))
        self._algo_combo.bind("<<ComboboxSelected>>", self._on_algorithm_selected)
        self._sync_algorithm_display()

        # --- step-by-step toggle ----------------------------------------
        toggle_row = ttk.Frame(self, style="Inset.TFrame", padding=(2, 2))
        toggle_row.pack(fill="x", pady=(0, 10))
        self._step_toggle = tk.Checkbutton(
            toggle_row,
            textvariable=self.step_mode_label,
            variable=self.step_mode,
            command=self._update_step_mode_toggle_ui,
            indicatoron=False,
            bd=0,
            relief="flat",
            highlightthickness=0,
            anchor="w",
            padx=10,
            pady=8,
            bg=self.palette["card_alt"],
            fg=self.palette["foreground"],
            activebackground=self.palette["card_alt"],
            activeforeground=self.palette["foreground"],
            selectcolor=self.palette["card_alt"],
            font=("Segoe UI Semibold", 11),
            cursor="hand2",
        )
        self._step_toggle.pack(fill="x")
        self._update_step_mode_toggle_ui()

        tk.Frame(self, height=1, bg=self.palette["card_alt"], bd=0).pack(
            fill="x", pady=4
        )

        # --- add process -------------------------------------------------
        ttk.Label(self, text="Add Process", style="Muted.TLabel").pack(anchor="w")
        form = ttk.Frame(self, style="Card.TFrame")
        form.pack(fill="x", pady=(2, 6))
        ttk.Entry(
            form, textvariable=self.new_name, width=6,
            font=("Segoe UI", 14),
        ).grid(
            row=0, column=0, padx=(0, 4), sticky="ew"
        )
        ttk.Entry(
            form, textvariable=self.new_size, width=6,
            font=("Segoe UI", 14),
        ).grid(
            row=0, column=1, padx=(0, 4), sticky="ew"
        )
        ttk.Button(form, text="Add", style="Primary.TButton",
                   command=self._add_process).grid(row=0, column=2)
        form.columnconfigure(0, weight=1)
        form.columnconfigure(1, weight=1)

        ttk.Label(
            self,
            text="Name / Size (in chosen unit)",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(0, 6))

        # --- process list ------------------------------------------------
        list_card = tk.Frame(self, bg=self.palette["card_alt"],
                             highlightthickness=1,
                             highlightbackground=self.palette["card"])
        list_card.pack(fill="both", expand=True, pady=(0, 8))
        self.process_list = tk.Listbox(
            list_card, height=8, bd=0,
            bg=self.palette["card_alt"],
            fg=self.palette["foreground"],
            selectbackground=self.palette["primary"],
            selectforeground="#ffffff",
            highlightthickness=0, activestyle="none",
            font=("Consolas", 14, "bold"),
        )
        self.process_list.pack(fill="both", expand=True, padx=1, pady=1)
        self.process_list.bind("<Button-3>", self._on_process_right_click)
        self.process_list.bind("<Button-2>", self._on_process_right_click)

        gen_row = ttk.Frame(self, style="Card.TFrame")
        gen_row.pack(fill="x", pady=(0, 10))
        for col in range(2):
            gen_row.columnconfigure(col, weight=1, uniform="workload-actions")
        ttk.Button(
            gen_row, text="Demo workload", style="Secondary.TButton",
            command=self._load_demo,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6), pady=2)
        ttk.Button(
            gen_row, text="Random workload", style="Secondary.TButton",
            command=self._load_random,
        ).grid(row=0, column=1, sticky="ew", padx=(6, 0), pady=2)
        ttk.Button(
            gen_row, text="Delete all", style="Secondary.TButton",
            command=self._clear_processes,
        ).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(6, 2))

        tk.Frame(self, height=1, bg=self.palette["card_alt"], bd=0).pack(
            fill="x", pady=4
        )

        # --- action buttons ---------------------------------------------
        ttk.Button(self, text="Run Allocation",
                   style="Primary.TButton",
                   command=self._on_run).pack(fill="x", pady=(4, 4))
        ttk.Button(self, text="Compare Algorithms",
                   command=self._on_compare).pack(fill="x", pady=2)
        ttk.Button(self, text="Compact Memory",
                   command=self._on_compact).pack(fill="x", pady=2)
        ttk.Button(self, text="Reset / New Session",
                   style="Danger.TButton",
                   command=self._on_reset).pack(fill="x", pady=(2, 0))

    # ------------------------------------------------------------------
    # Process management
    # ------------------------------------------------------------------
    def _add_process(self) -> None:
        name = self.new_name.get().strip() or f"P{len(self.processes) + 1}"
        size_str = self.new_size.get().strip()
        if any(
            p.get("op", "alloc") == "alloc"
            and p.get("name", "").strip().lower() == name.lower()
            for p in self.processes
        ):
            messagebox.showerror(
                "Duplicate process",
                f"A process named '{name}' already exists. Use a unique name.",
            )
            return
        try:
            size = int(size_str)
        except ValueError:
            messagebox.showerror("Invalid size",
                                 "Process size must be a positive integer (C-04).")
            return
        if size <= 0:
            messagebox.showerror("Invalid size",
                                 "Process size must be > 0 (FR-02).")
            return
        if len(self.processes) >= 100:
            messagebox.showerror("Too many processes",
                                 "Maximum of 100 concurrent processes (C-06).")
            return
        color_index = sum(1 for p in self.processes
                          if p.get("op", "alloc") == "alloc") % 8
        self.processes.append({
            "op": "alloc", "name": name, "size": size, "color_index": color_index,
        })
        self.new_name.set("")
        self.new_size.set("")
        self._refresh_process_list()
        self._on_change()

    def _remove_process(self) -> None:
        selection = self.process_list.curselection()
        if not selection:
            return
        idx = selection[0]
        self.processes.pop(idx)
        self._refresh_process_list()
        self._on_change()

    def _add_free_event(self) -> None:
        selection = self.process_list.curselection()
        if not selection:
            messagebox.showinfo(
                "Choose a process",
                "Select an allocation entry, then add a matching free event.",
            )
            return
        selected = self.processes[selection[0]]
        if selected.get("op", "alloc") == "free":
            messagebox.showinfo(
                "Choose an allocation",
                "Select an ALLOC row, then add a matching free event.",
            )
            return
        name = selected.get("name", "").strip()
        if not name:
            return
        if any(
            p.get("op", "alloc") == "free"
            and p.get("name", "").strip().lower() == name.lower()
            for p in self.processes
        ):
            messagebox.showinfo(
                "Already freed",
                f"A FREE event for {name} already exists.",
            )
            return
        insert_at = len(self.processes)
        self.processes.append({"op": "free", "name": name, "size": 0})
        self._refresh_process_list()
        self.process_list.selection_clear(0, tk.END)
        self.process_list.selection_set(insert_at)
        self.process_list.see(insert_at)
        self._on_change()

    def _on_process_right_click(self, event) -> str:
        idx = self.process_list.nearest(event.y)
        if 0 <= idx < len(self.processes):
            self.process_list.selection_clear(0, tk.END)
            self.process_list.selection_set(idx)
            self.process_list.activate(idx)
            self._show_process_menu(event.x_root, event.y_root, idx)
        return "break"

    def _show_process_menu(self, x: int, y: int, idx: int) -> None:
        selected = self.processes[idx]
        menu = tk.Menu(
            self,
            tearoff=False,
            bg=self.palette["card"],
            fg=self.palette["foreground"],
            activebackground=self.palette["primary"],
            activeforeground=self.palette["primary_fg"],
            disabledforeground=self.palette["muted"],
            font=("Segoe UI", 11),
            relief="solid",
            bd=1,
        )
        if selected.get("op", "alloc") == "alloc":
            menu.add_command(
                label=f"Add FREE event for {selected.get('name', '')}",
                command=self._add_free_event,
            )
        else:
            menu.add_command(label="FREE event already selected", state="disabled")
        menu.add_separator()
        menu.add_command(label="Delete selected row", command=self._remove_process)
        try:
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def _clear_processes(self) -> None:
        self.processes = []
        self._refresh_process_list()
        self._on_change()

    def _load_demo(self) -> None:
        self.total_memory.set(512)
        self.unit.set("KB")
        self.algorithm.set("first-fit")
        self._sync_algorithm_display()
        self.processes = [
            {"op": "alloc", "name": "P1", "size": 100, "color_index": 0},
            {"op": "alloc", "name": "P2", "size": 120, "color_index": 1},
            {"op": "alloc", "name": "P3", "size":  80, "color_index": 2},
            {"op": "alloc", "name": "P4", "size": 100, "color_index": 3},
            {"op": "free",  "name": "P2", "size": 0},
            {"op": "free",  "name": "P4", "size": 0},
            {"op": "alloc", "name": "P5", "size":  70, "color_index": 4},
            {"op": "alloc", "name": "P6", "size": 150, "color_index": 5},
        ]
        self._refresh_process_list()
        self._on_change()

    def _on_algorithm_selected(self, _event=None) -> None:
        selected = self.algorithm_label.get()
        key = self._algo_keys_by_label.get(selected)
        if key is None:
            return
        self.algorithm.set(key)
        self._on_change()

    def _sync_algorithm_display(self) -> None:
        self.algorithm_label.set(
            self._algo_labels.get(self.algorithm.get(), self.algorithm.get())
        )

    def _refresh_algorithm_choices(self) -> None:
        """Re-apply dropdown items before opening the popup list."""
        self._algo_combo.configure(values=tuple(self._algo_labels.values()))

    def _update_step_mode_toggle_ui(self) -> None:
        if self.step_mode.get():
            self.step_mode_label.set("● Step-by-step mode")
            self._step_toggle.configure(
                fg=self.palette["warning"],
                activeforeground=self.palette["warning"],
            )
        else:
            self.step_mode_label.set("○ Step-by-step mode")
            self._step_toggle.configure(
                fg=self.palette["muted"],
                activeforeground=self.palette["muted"],
            )

    def _load_random(self) -> None:
        """Generate a varied random workload with valid alloc/free events."""
        scale = unit_scale(self.unit.get())
        minimum = 8 if scale == 1024 else 128
        current = int(self.total_memory.get() or (32 if scale == 1024 else 512))
        display_total = max(minimum, current)
        display_total = min(display_total, max(1, 1_000_000 // scale))
        self.total_memory.set(display_total)

        def random_size() -> int:
            # Mostly ordinary jobs, with occasional larger ones that may expose
            # fit failures or sharper algorithm differences.
            if random.random() < 0.15:
                fraction = random.uniform(0.28, 0.45)
            else:
                fraction = random.uniform(0.06, 0.24)
            return max(1, int(display_total * fraction))

        self.processes = []
        resident: list[str] = []
        freed: set[str] = set()
        next_num = 1

        def add_alloc() -> str:
            nonlocal next_num
            name = f"P{next_num}"
            next_num += 1
            self.processes.append({
                "op": "alloc",
                "name": name,
                "size": random_size(),
                "color_index": (next_num - 2) % 8,
            })
            resident.append(name)
            return name

        def add_free() -> bool:
            choices = [name for name in resident if name not in freed]
            if not choices:
                return False
            name = random.choice(choices)
            resident.remove(name)
            freed.add(name)
            self.processes.append({"op": "free", "name": name, "size": 0})
            return True

        # Seed with a few allocations so frees can create middle holes.
        for _ in range(random.randint(3, 5)):
            add_alloc()

        target_events = random.randint(9, 15)
        while len(self.processes) < target_events:
            should_free = (
                bool(resident)
                and len(freed) < 5
                and (len(resident) >= 4 or random.random() < 0.35)
            )
            if should_free and add_free():
                # Often allocate soon after a free so the next process must
                # choose between fragmented holes.
                if len(self.processes) < target_events and random.random() < 0.7:
                    add_alloc()
            else:
                add_alloc()

        # Guarantee at least one free and one later allocation.
        if not freed and len(self.processes) >= 3:
            victim = self.processes[random.randint(1, min(3, len(self.processes) - 1))]
            if victim.get("op") == "alloc":
                self.processes.append({"op": "free", "name": victim["name"], "size": 0})
                self.processes.append({
                    "op": "alloc",
                    "name": f"P{next_num}",
                    "size": random_size(),
                    "color_index": (next_num - 1) % 8,
                })
        self._refresh_process_list()
        self._on_change()

    def set_processes(self, procs: list[dict]) -> None:
        """Used by undo/redo to restore a previous process list snapshot."""
        self.processes = [dict(p) for p in procs]
        self._refresh_process_list()
        self._on_change()

    def _refresh_process_list(self) -> None:
        self.process_list.delete(0, tk.END)
        self.process_list.configure(
            bg=self.palette["card_alt"],
            fg=self.palette["foreground"],
            selectbackground=self.palette["primary"],
        )
        alloc_colors = {
            p.get("name", "").strip().lower(): color_for_process(
                p.get("color_index", 0)
            )
            for p in self.processes
            if p.get("op", "alloc") == "alloc"
        }
        for i, p in enumerate(self.processes):
            if p.get("op", "alloc") == "free":
                self.process_list.insert(tk.END, f"  FREE   {p['name']:<6}")
                free_color = alloc_colors.get(
                    p.get("name", "").strip().lower(),
                    self.palette["warning"],
                )
                self.process_list.itemconfig(i, foreground=free_color)
            else:
                self.process_list.insert(
                    tk.END,
                    f"  ALLOC  {p['name']:<6}{p['size']:>6} {self.unit.get()}",
                )
                self.process_list.itemconfig(
                    i, foreground=color_for_process(p.get("color_index", 0))
                )

    # ------------------------------------------------------------------
    # Public accessors
    # ------------------------------------------------------------------
    def resolved_total_memory(self) -> int:
        """Return total memory normalised to KB."""
        raw = self.total_memory.get()
        return raw * unit_scale(self.unit.get())
