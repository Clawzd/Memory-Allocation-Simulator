"""Main window + controller wiring (pro edition).

Re-creates the structure of ``OS-Project/src/pages/Home.jsx`` in Tkinter
and then goes further: animated memory map, fragmentation sparkline,
undo/redo history, command palette, random workload generator, text
report export, and a live status bar.

Priority order (TASKS.md): PDF requirements first, website style second,
polish third.
"""

from __future__ import annotations

import copy
import datetime as _dt
import ctypes
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Optional

from .algorithms import (
    WorkloadEvent,
    compare_workload_algorithms,
    generate_workload_steps,
    pretty_name,
)
from .model import (
    MAX_MEMORY_SIZE,
    MemoryBlock,
    MemoryManager,
    Process,
    unit_scale,
    validate_processes,
)
from .theme import apply_theme
from .views import (
    CommandPalette,
    ComparisonDialog,
    ControlPanel,
    EducationalSection,
    FragmentationChart,
    MemoryMap,
    StatsPanel,
    StatusBar,
    StepControls,
    StepLog,
    ToastManager,
)


HISTORY_LIMIT = 50


# ---------------------------------------------------------------------------


class MemorySimulatorApp(tk.Tk):
    """Top-level window hosting all views and controller logic."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Memory Allocation Simulator")
        self.geometry("1760x980")
        self.minsize(1480, 860)

        self.dark_mode = tk.BooleanVar(value=True)
        self.palette = apply_theme(self, dark=True)
        self._apply_title_bar_color()

        # --- controller state ------------------------------------------------
        self._steps: list[dict] = []
        self._current_step: int = -1
        self._is_running: bool = False
        self._is_playing: bool = False
        self._auto_speed: int = 1000
        self._autoplay_after: Optional[str] = None
        self._live_blocks: Optional[list[dict]] = None

        # history stacks for undo/redo (snapshots of the process-list config)
        self._undo_stack: list[list[dict]] = []
        self._redo_stack: list[list[dict]] = []
        self._last_config_snapshot: Optional[list[dict]] = None
        self._suppress_history: bool = False

        # history series for the sparkline
        self._util_history: list[float] = []
        self._frag_history: list[float] = []
        self._event_types: list[str] = []

        self._build_layout()
        self._bind_keys()
        self._snapshot_config()   # seed baseline for undo
        self._refresh_view()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def _build_layout(self) -> None:
        self._build_header()

        outer = ttk.Frame(self, padding=(16, 6, 16, 10))
        outer.pack(fill="both", expand=True)

        outer.columnconfigure(0, weight=0, minsize=520)
        outer.columnconfigure(1, weight=1)
        outer.columnconfigure(2, weight=0, minsize=500)
        outer.rowconfigure(0, weight=1)

        # Left column -------------------------------------------------------
        self.control_panel = ControlPanel(
            outer, palette=self.palette,
            on_run=self._on_run,
            on_reset=self._on_reset,
            on_compare=self._on_compare,
            on_compact=self._on_compact,
            on_change=self._on_config_change,
        )
        self.control_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        # Center column -----------------------------------------------------
        center = ttk.Frame(outer)
        center.grid(row=0, column=1, sticky="nsew")
        center.columnconfigure(0, weight=1)
        self._center = center
        center.rowconfigure(0, weight=3, minsize=260)
        center.rowconfigure(1, weight=2, minsize=220)
        center.rowconfigure(2, weight=0)
        center.rowconfigure(3, weight=0, minsize=0)

        self.memory_map = MemoryMap(
            center, palette=self.palette, on_deallocate=self._on_deallocate,
        )
        self.memory_map.grid(row=0, column=0, sticky="nsew")

        self.frag_chart = FragmentationChart(
            center, palette=self.palette, on_jump=self._on_jump,
        )
        self.frag_chart.grid(row=1, column=0, sticky="nsew", pady=(10, 0))

        self.step_controls = StepControls(
            center, palette=self.palette,
            on_prev=self._on_prev,
            on_next=self._on_next,
            on_toggle_play=self._on_toggle_play,
            on_restart=self._on_restart,
            on_speed_change=self._on_speed_change,
        )
        self.step_controls.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        self.step_controls.grid_remove()

        self.step_log = StepLog(
            center, palette=self.palette, on_jump=self._on_jump,
        )
        self.step_log.grid(row=3, column=0, sticky="nsew", pady=(10, 0))
        self.step_log.grid_remove()

        # Right column ------------------------------------------------------
        right = ttk.Frame(outer)
        right.grid(row=0, column=2, sticky="nsew", padx=(12, 0))
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=3)
        right.rowconfigure(1, weight=1)

        self.stats_panel = StatsPanel(right, palette=self.palette)
        self.stats_panel.grid(row=0, column=0, sticky="nsew")

        self.edu = EducationalSection(right, palette=self.palette)
        self.edu.grid(row=1, column=0, sticky="nsew", pady=(10, 0))

        # Status bar --------------------------------------------------------
        self.status = StatusBar(self, palette=self.palette)
        self.status.pack(fill="x", side="bottom")

        # Toast manager
        self.toasts = ToastManager(self, self.palette)

    def _build_header(self) -> None:
        header = ttk.Frame(self, style="Header.TFrame", padding=(16, 10))
        header.pack(fill="x")

        left = ttk.Frame(header, style="Header.TFrame")
        left.pack(side="left", fill="y")
        icon = tk.Label(
            left, text="\u2328",
            bg=self.palette["primary"], fg="#ffffff",
            font=("Segoe UI", 13, "bold"),
            padx=10, pady=4,
        )
        icon.pack(side="left", padx=(0, 12))
        title_wrap = ttk.Frame(left, style="Header.TFrame")
        title_wrap.pack(side="left")
        ttk.Label(title_wrap, text="Memory Allocation Simulator",
                  style="AppTitle.TLabel").pack(anchor="w")
        ttk.Label(title_wrap,
                  text="Interactive OS memory management visualization",
                  style="AppSubtitle.TLabel").pack(anchor="w")

        right = ttk.Frame(header, style="Header.TFrame")
        right.pack(side="right")

        self.header_compact_btn = ttk.Button(
            right, text="Compact", command=self._on_compact,
        )
        self.header_compact_btn.pack(side="right", padx=4)
        self.header_compact_btn.state(["disabled"])

        ttk.Button(
            right, text="\u263c / \u263e  Theme", command=self._toggle_theme,
        ).pack(side="right", padx=4)

    # ------------------------------------------------------------------
    # Keyboard shortcuts
    # ------------------------------------------------------------------
    def _bind_keys(self) -> None:
        self.bind("<Left>",   lambda _e: self._is_running and self._on_prev())
        self.bind("<Right>",  lambda _e: self._is_running and self._on_next())
        self.bind("<space>",  self._space_handler)
        self.bind("r",        lambda _e: self._is_running and self._on_restart())
        self.bind("R",        lambda _e: self._is_running and self._on_restart())

        self.bind("<Control-k>", lambda _e: self._open_command_palette())
        self.bind("<Control-K>", lambda _e: self._open_command_palette())
        self.bind("<Control-r>", lambda _e: self._on_run())
        self.bind("<Control-R>", lambda _e: self._on_run())
        self.bind("<Control-e>", lambda _e: self._export_report())
        self.bind("<Control-E>", lambda _e: self._export_report())
        self.bind("<Control-z>", lambda _e: self._on_undo())
        self.bind("<Control-Z>", lambda _e: self._on_undo())
        self.bind("<Control-y>", lambda _e: self._on_redo())
        self.bind("<Control-Y>", lambda _e: self._on_redo())
        self.bind("<Control-Shift-z>", lambda _e: self._on_redo())
        self.bind("<Control-Shift-Z>", lambda _e: self._on_redo())

    def _space_handler(self, event):
        if isinstance(event.widget, (tk.Entry, tk.Text)):
            return  # don't hijack space inside text inputs
        if self._is_running:
            self._on_toggle_play()
        return "break"

    # ------------------------------------------------------------------
    # Command palette
    # ------------------------------------------------------------------
    def _actions(self) -> list[tuple[str, str, callable]]:
        return [
            ("Run allocation",              "Ctrl+R",     self._on_run),
            ("Reset / New Session",         "",           self._on_reset),
            ("Compact memory",              "",           self._on_compact),
            ("Compare all algorithms",      "",           self._on_compare),
            ("Undo",                        "Ctrl+Z",     self._on_undo),
            ("Redo",                        "Ctrl+Y",     self._on_redo),
            ("Export text report",          "Ctrl+E",     self._export_report),
            ("Toggle theme (dark/light)",   "",           self._toggle_theme),
            ("Load demo workload",          "",
             self.control_panel._load_demo),
            ("Generate random workload",    "",
             self.control_panel._load_random),
            ("Clear all processes",         "",
             self.control_panel._clear_processes),
            ("Next step",                   "\u2192",     self._on_next),
            ("Previous step",               "\u2190",     self._on_prev),
            ("Play / Pause",                "Space",      self._on_toggle_play),
            ("Restart simulation",          "R",          self._on_restart),
        ]

    def _open_command_palette(self) -> None:
        try:
            CommandPalette(self, palette=self.palette, actions=self._actions())
        except Exception as exc:  # pragma: no cover - safety net
            self.toasts.show("Palette error", str(exc), variant="destructive")

    # ------------------------------------------------------------------
    # Theme toggle
    # ------------------------------------------------------------------
    def _toggle_theme(self) -> None:
        self.dark_mode.set(not self.dark_mode.get())
        self.palette = apply_theme(self, dark=self.dark_mode.get())
        self._propagate_palette()
        self._apply_title_bar_color()
        # Tkinter ttk re-styling applies immediately, but custom Canvas
        # widgets need a refresh.
        self._refresh_view()
        self.toasts.show(
            "Theme updated",
            f"Switched to {'dark' if self.dark_mode.get() else 'light'} mode.",
            variant="success",
        )

    def _propagate_palette(self) -> None:
        """Give custom Tk widgets the newly selected palette."""
        widgets = (
            self.control_panel,
            self.memory_map,
            self.frag_chart,
            self.stats_panel,
            self.edu,
            self.status,
            self.toasts,
        )
        for widget in widgets:
            try:
                if hasattr(widget, "apply_palette"):
                    widget.apply_palette(self.palette)
                else:
                    widget.palette = self.palette
            except Exception:
                pass
        try:
            self.control_panel._refresh_process_list()
        except Exception:
            pass

    def _apply_title_bar_color(self) -> None:
        """Tint the native Windows title bar to match the current theme."""
        if sys.platform != "win32":
            return

        def colorref(hex_color: str) -> int:
            r = int(hex_color[1:3], 16)
            g = int(hex_color[3:5], 16)
            b = int(hex_color[5:7], 16)
            return r | (g << 8) | (b << 16)

        try:
            self.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            if not hwnd:
                hwnd = self.winfo_id()

            dark_enabled = ctypes.c_int(1 if self.dark_mode.get() else 0)
            # Attribute 20 is the current dark-title-bar flag; 19 covers
            # older Windows 10 builds that used the previous id.
            for attr in (20, 19):
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd,
                    attr,
                    ctypes.byref(dark_enabled),
                    ctypes.sizeof(dark_enabled),
                )

            caption = ctypes.c_int(colorref(self.palette["card"]))
            text = ctypes.c_int(colorref(self.palette["foreground"]))
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 35, ctypes.byref(caption), ctypes.sizeof(caption)
            )
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 36, ctypes.byref(text), ctypes.sizeof(text)
            )
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Undo / Redo
    # ------------------------------------------------------------------
    def _snapshot_config(self) -> None:
        """Push the current process-list configuration onto the undo stack."""
        if self._suppress_history:
            return
        current = [dict(p) for p in self.control_panel.processes]
        if self._last_config_snapshot == current:
            return
        if self._last_config_snapshot is not None:
            self._undo_stack.append(self._last_config_snapshot)
            if len(self._undo_stack) > HISTORY_LIMIT:
                self._undo_stack.pop(0)
            self._redo_stack.clear()
        self._last_config_snapshot = current

    def _on_undo(self) -> None:
        if not self._undo_stack:
            self.toasts.show("Nothing to undo")
            return
        if self._last_config_snapshot is not None:
            self._redo_stack.append(self._last_config_snapshot)
        prev = self._undo_stack.pop()
        self._last_config_snapshot = prev
        self._apply_config(prev)
        self.toasts.show("Undo", f"Restored to {len(prev)} process(es).")

    def _on_redo(self) -> None:
        if not self._redo_stack:
            self.toasts.show("Nothing to redo")
            return
        if self._last_config_snapshot is not None:
            self._undo_stack.append(self._last_config_snapshot)
        nxt = self._redo_stack.pop()
        self._last_config_snapshot = nxt
        self._apply_config(nxt)
        self.toasts.show("Redo", f"Restored to {len(nxt)} process(es).")

    def _apply_config(self, procs: list[dict]) -> None:
        self._suppress_history = True
        try:
            self.control_panel.set_processes(procs)
        finally:
            self._suppress_history = False

    # ------------------------------------------------------------------
    # Workload helpers
    # ------------------------------------------------------------------
    def _gather_processes(self) -> list[Process]:
        scale = unit_scale(self.control_panel.unit.get())
        out: list[Process] = []
        for i, p in enumerate(self.control_panel.processes):
            if p.get("op", "alloc") == "free":
                continue
            out.append(Process(
                name=p["name"],
                size=int(p["size"]) * scale,
                color_index=p.get("color_index", i),
            ))
        return out

    def _gather_workload(self) -> list[WorkloadEvent]:
        scale = unit_scale(self.control_panel.unit.get())
        events: list[WorkloadEvent] = []
        color_index = 0
        for p in self.control_panel.processes:
            if p.get("op", "alloc") == "free":
                events.append(WorkloadEvent.free(p["name"]))
                continue
            events.append(WorkloadEvent.alloc(Process(
                name=p["name"],
                size=int(p["size"]) * scale,
                color_index=p.get("color_index", color_index),
            )))
            color_index += 1
        return events

    def _current_total(self) -> int:
        return int(self.control_panel.resolved_total_memory())

    # ------------------------------------------------------------------
    # Controller: RUN
    # ------------------------------------------------------------------
    def _on_run(self) -> None:
        try:
            total = self._current_total()
            if total <= 0:
                raise ValueError("Total memory must be > 0 (FR-01).")
            if total > MAX_MEMORY_SIZE:
                raise ValueError(
                    f"Total memory must be \u2264 {MAX_MEMORY_SIZE} (C-05)."
                )
            workload = self._gather_workload()
            processes = [e.process for e in workload
                         if e.op == "alloc" and e.process is not None]
            if not processes:
                raise ValueError("Add at least one allocation before running.")
            validate_processes(processes, total)
        except ValueError as exc:
            self.toasts.show("Invalid input", str(exc), variant="destructive")
            return

        algorithm = self.control_panel.algorithm.get()
        self._steps = generate_workload_steps(total, workload, algorithm)
        self._build_history_series()

        step_mode = self.control_panel.step_mode.get()
        # Always begin from the first step; do not reveal final state upfront.
        self._current_step = 0
        self._is_running = True
        # Step mode: manual progression. Non-step mode: autoplay.
        self._is_playing = bool(not step_mode and len(self._steps) > 1)
        self._live_blocks = None
        self._cancel_autoplay()
        self._show_run_widgets(True)
        if self._is_playing:
            # Ensure auto mode visibly starts immediately after Run.
            self._current_step = min(1, len(self._steps) - 1)
            self._refresh_view(animate=False)
            self._schedule_autoplay()
        else:
            self._refresh_view(animate=False)
        self.toasts.show(
            "Allocation ready",
            f"{pretty_name(algorithm)} \u00b7 {len(self._steps)} steps.",
            variant="success",
        )

    def _on_reset(self) -> None:
        self._steps = []
        self._current_step = -1
        self._is_running = False
        self._is_playing = False
        self._live_blocks = None
        self._util_history = []
        self._frag_history = []
        self._event_types = []
        self._cancel_autoplay()
        self._show_run_widgets(False)
        self.frag_chart.reset()
        self._refresh_view(animate=False)
        self.toasts.show("Session reset", "Memory returned to empty state.")

    def _on_compare(self) -> None:
        try:
            total = self._current_total()
            workload = self._gather_workload()
            processes = [e.process for e in workload
                         if e.op == "alloc" and e.process is not None]
            validate_processes(processes, total)
        except ValueError as exc:
            self.toasts.show("Invalid input", str(exc), variant="destructive")
            return
        results = compare_workload_algorithms(total, workload)
        ComparisonDialog(self, palette=self.palette, results=results)

    def _on_compact(self) -> None:
        blocks = self._displayed_blocks()
        if blocks is None:
            return
        mm = self._mm_from_blocks(blocks)
        mm.compact()
        self._live_blocks = [b.to_dict() for b in mm.blocks]
        self._refresh_view()
        self.toasts.show("Memory compacted",
                         "All processes packed to low addresses.",
                         variant="success")

    def _on_deallocate(self, process_name: str) -> None:
        blocks = self._displayed_blocks()
        if blocks is None:
            return
        mm = self._mm_from_blocks(blocks)
        if not mm.deallocate_by_name(process_name):
            return
        self._live_blocks = [b.to_dict() for b in mm.blocks]
        self._is_playing = False
        self._cancel_autoplay()
        self._refresh_view()
        self.toasts.show(
            f"Deallocated {process_name}",
            "Memory block freed, holes coalesced.",
            variant="success",
        )

    # ------------------------------------------------------------------
    # Controller: STEP navigation
    # ------------------------------------------------------------------
    def _on_next(self) -> None:
        if not self._steps:
            return
        if self._current_step < len(self._steps) - 1:
            self._current_step += 1
            self._live_blocks = None
            self._refresh_view()

    def _on_prev(self) -> None:
        if not self._steps:
            return
        if self._current_step > 0:
            self._current_step -= 1
            self._live_blocks = None
            self._refresh_view()

    def _on_restart(self) -> None:
        if not self._steps:
            return
        self._current_step = 0
        self._is_playing = False
        self._live_blocks = None
        self._cancel_autoplay()
        self._refresh_view()

    def _on_jump(self, step_index: int) -> None:
        if not self._steps:
            return
        self._current_step = max(0, min(len(self._steps) - 1, step_index))
        self._live_blocks = None
        self._cancel_autoplay()
        self._is_playing = False
        self._refresh_view()

    def _on_toggle_play(self) -> None:
        if not self._steps:
            return
        if self._current_step >= len(self._steps) - 1:
            self._current_step = 0
        self._is_playing = not self._is_playing
        self._live_blocks = None
        if self._is_playing:
            self._schedule_autoplay()
        else:
            self._cancel_autoplay()
        self._refresh_view()

    def _on_speed_change(self, ms: int) -> None:
        self._auto_speed = max(100, int(ms))

    def _schedule_autoplay(self) -> None:
        self._cancel_autoplay()
        self._autoplay_after = self.after(self._auto_speed, self._autoplay_tick)

    def _cancel_autoplay(self) -> None:
        if self._autoplay_after is not None:
            try:
                self.after_cancel(self._autoplay_after)
            except Exception:
                pass
            self._autoplay_after = None

    def _autoplay_tick(self) -> None:
        if not self._is_playing:
            return
        if self._current_step < len(self._steps) - 1:
            self._current_step += 1
            self._live_blocks = None
            self._refresh_view()
            self._schedule_autoplay()
        else:
            self._is_playing = False
            self._refresh_view()

    def _on_config_change(self) -> None:
        self._snapshot_config()
        if self._is_running:
            self._on_reset()
        else:
            self._refresh_view(animate=False)

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------
    def _export_report(self) -> None:
        blocks = self._displayed_blocks() or []
        stats = self._stats_for_blocks(blocks)
        algo = self.control_panel.algorithm.get()

        lines: list[str] = []
        stamp = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines.append("=" * 60)
        lines.append(" ICS 433 - Memory Allocation Simulator report")
        lines.append(f" Generated: {stamp}")
        lines.append("=" * 60)
        lines.append("")
        lines.append(f"Algorithm     : {pretty_name(algo)}")
        lines.append(f"Total memory  : {stats['total']} KB")
        lines.append(f"Used          : {stats['used']} KB ({stats['utilization']}%)")
        lines.append(f"Free          : {stats['free']} KB ({stats['free_percent']}%)")
        lines.append(f"Free holes    : {stats['num_holes']}")
        lines.append(f"Largest hole  : {stats['largest_free']} KB")
        lines.append(f"Ext. fragment : {stats['external_fragmentation']}%")
        lines.append(f"Processes     : {stats['process_count']}")
        lines.append("")
        lines.append("Memory map (address ranges):")
        for b in blocks:
            if b["is_free"]:
                lines.append(f"  [{b['start']:>6} - {b['end']:>6}]  FREE      {b['size']} KB")
            else:
                lines.append(
                    f"  [{b['start']:>6} - {b['end']:>6}]  {b['name']:<8}  {b['size']} KB"
                )
        lines.append("")
        if self._steps:
            lines.append("Step log:")
            for i, s in enumerate(self._steps):
                lines.append(f"  {i+1:>3}. [{s['type']}] {s['message']}")
            lines.append("")
        lines.append("-- End of report --")
        text = "\n".join(lines)

        path = filedialog.asksaveasfilename(
            parent=self,
            title="Save report",
            defaultextension=".txt",
            initialfile=f"memory_report_{stamp.replace(':', '-').replace(' ', '_')}.txt",
            filetypes=[("Text file", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
        except OSError as exc:
            self.toasts.show("Export failed", str(exc), variant="destructive")
            return
        self.toasts.show("Report saved",
                         f"Written to {path}", variant="success")

    # ------------------------------------------------------------------
    # Rendering helpers
    # ------------------------------------------------------------------
    def _displayed_blocks(self) -> Optional[list[dict]]:
        if self._live_blocks is not None:
            return copy.deepcopy(self._live_blocks)
        if self._is_running and 0 <= self._current_step < len(self._steps):
            return copy.deepcopy(self._steps[self._current_step]["blocks"])
        total = self._current_total()
        if total <= 0 or total > MAX_MEMORY_SIZE:
            return None
        return [MemoryBlock(0, total, True).to_dict()]

    def _mm_from_blocks(self, blocks: list[dict]) -> MemoryManager:
        total = sum(b["size"] for b in blocks) or self._current_total()
        mm = MemoryManager(max(1, total))
        rebuilt: list[MemoryBlock] = []
        for b in blocks:
            rebuilt.append(MemoryBlock(
                start_address=b["start"],
                size=b["size"],
                is_free=b["is_free"],
                process_id=b.get("process_id"),
                process_name=b.get("name"),
                color_index=b.get("color_index", 0),
                id=b["id"],
            ))
        mm.blocks = rebuilt
        return mm

    def _stats_for_blocks(self, blocks: list[dict]) -> dict:
        used = sum(b["size"] for b in blocks if not b["is_free"])
        total = sum(b["size"] for b in blocks) or self._current_total()
        free = total - used
        holes = [b for b in blocks if b["is_free"]]
        largest_free = max((b["size"] for b in holes), default=0)
        util = (used / total * 100) if total else 0.0
        ext_frag = ((free - largest_free) / free * 100) if free > 0 else 0.0
        return {
            "total": total,
            "used": used,
            "free": free,
            "used_percent": round(util, 1),
            "free_percent": round(100 - util, 1),
            "num_holes": len(holes),
            "largest_free": largest_free,
            "external_fragmentation": round(ext_frag, 1),
            "utilization": round(util, 1),
            "process_count": sum(1 for b in blocks if not b["is_free"]),
        }

    def _build_history_series(self) -> None:
        """Build utilization & fragmentation series across every step."""
        self._util_history = []
        self._frag_history = []
        self._event_types: list[str] = []
        for s in self._steps:
            st = self._stats_for_blocks(s["blocks"])
            self._util_history.append(st["utilization"])
            self._frag_history.append(st["external_fragmentation"])
            self._event_types.append(s["type"])

    def _show_run_widgets(self, show: bool) -> None:
        if show:
            self._center.rowconfigure(0, weight=2, minsize=240)
            self._center.rowconfigure(1, weight=1, minsize=190)
            self._center.rowconfigure(3, weight=2, minsize=230)
            self.step_controls.grid()
            self.step_log.grid()
            self.header_compact_btn.state(["!disabled"])
        else:
            self.step_controls.grid_remove()
            self.step_log.grid_remove()
            self._center.rowconfigure(0, weight=3, minsize=260)
            self._center.rowconfigure(1, weight=2, minsize=220)
            self._center.rowconfigure(3, weight=0, minsize=0)
            self.header_compact_btn.state(["disabled"])

    def _refresh_view(self, *, animate: bool = True) -> None:
        blocks = self._displayed_blocks()
        if blocks is None:
            blocks = []
        total = sum(b["size"] for b in blocks) or self._current_total()

        step_data = (
            self._steps[self._current_step]
            if self._is_running and 0 <= self._current_step < len(self._steps)
            else None
        )
        scan_id = step_data["scanning_block_id"] if step_data else None
        fit_id = (
            step_data["scanning_block_id"]
            if step_data and step_data["type"] == "scanning-fit"
            else None
        )
        if fit_id:
            scan_id = None

        algorithm = self.control_panel.algorithm.get()
        algo_label = pretty_name(algorithm).upper() if self._is_running else ""

        self.memory_map.set_state(
            blocks, total,
            scan_id=scan_id, fit_id=fit_id,
            algorithm_label=algo_label,
            live=self._live_blocks is not None,
            animate=animate,
        )
        stats = self._stats_for_blocks(blocks)
        self.stats_panel.update_state(blocks, stats)

        if self._is_running:
            visible_steps = self._steps[: self._current_step + 1]
            self.step_log.set_steps(visible_steps, len(visible_steps) - 1)
            self.step_controls.set_state(
                self._current_step, len(self._steps), self._is_playing,
            )
            # Reveal history progressively; do not show future points yet.
            if self._util_history:
                self.frag_chart.update_history(
                    self._util_history[: self._current_step + 1],
                    self._frag_history[: self._current_step + 1],
                    event_types=self._event_types[: self._current_step + 1],
                    current=len(self._util_history[: self._current_step + 1]) - 1,
                )
            # status bar
            self.status.set_running(
                pretty_name(algorithm), self._current_step, len(self._steps),
            )
        else:
            if self._live_blocks is not None:
                self.status.set_live("manually edited memory")
            else:
                self.status.set_ready()

        self.status.set_metrics(
            stats["used"], stats["total"],
            stats["utilization"], stats["external_fragmentation"],
        )

    # ------------------------------------------------------------------
    def destroy(self) -> None:  # override to cancel pending callbacks
        self._cancel_autoplay()
        super().destroy()


# ---------------------------------------------------------------------------


def main() -> None:
    app = MemorySimulatorApp()
    app.mainloop()


if __name__ == "__main__":
    main()
