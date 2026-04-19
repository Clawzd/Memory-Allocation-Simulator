# Memory Allocation Simulator (Python / Tkinter)

ICS 433 - Operating Systems, Phase 1.

Python/Tkinter desktop re-implementation of the companion web app
(`../OS-Project`). Fully satisfies every Functional Requirement
(FR-01 - FR-09) and respects every constraint (C-01 - C-08) defined in
`ICS433_Phase1_MemoryAllocationSimulator.pdf`, while matching the web
app's three-panel layout, colour palette, and interaction flow.

## Features

| PDF ID | Feature | Where implemented |
| --- | --- | --- |
| FR-01 | Configure total memory (KB / MB)                         | `views/control_panel.py` |
| FR-02 | Add / remove processes                                   | `views/control_panel.py` |
| FR-03 | First / Best / Worst / Next Fit                          | `algorithms.py` |
| FR-04 | Allocate on Run, report when no hole fits                | `app.py` -> `_on_run` |
| FR-05 | Visual memory map with address ranges                    | `views/memory_map.py` |
| FR-06 | Live statistics + process table                          | `views/stats_panel.py` |
| FR-07 | Compact memory                                           | `model.py::compact` |
| FR-08 | Reset / new session                                      | `app.py` -> `_on_reset` |
| FR-09 | Step-by-step mode (Prev / Next / Play / Restart)         | `views/step_controls.py` |

Non-functional targets (PDF 1.3):

* **Usability** - labelled inputs, tooltips on every memory block.
* **Performance** - Canvas-based redraw; handles 10 000 units x 50 processes in <1 s.
* **Portability** - Tkinter ships with CPython, runs on Windows / macOS / Linux.
* **Accuracy** - 16 unit tests verify algorithm correctness, hole coalescing, and stats.
* **Reliability** - every user input passes `validate_processes` before reaching the model.

## Install & Run

Requires Python >= 3.11. Tkinter is included with the standard Python
installer on Windows and macOS.

On Windows:

```powershell
cd OSPpy
python -m memory_sim
```

If `python` is not recognized, install Python from
<https://www.python.org/downloads/windows/> and enable **Add python.exe to PATH**
during installation.

On some Linux distros, install Tkinter first:

```bash
sudo apt install python3-tk        # Debian / Ubuntu
sudo dnf install python3-tkinter   # Fedora
```

Run directly from the folder:

```bash
cd OSPpy
python -m memory_sim
```

Or install as a package (editable mode for development):

```bash
cd OSPpy
pip install -e .
memory-sim
```

## Tests

```bash
cd OSPpy
python -m pytest tests/ -q
```

All 16 tests pass. Coverage spans every algorithm (including Next-Fit
wrap-around), hole splitting, immediate coalescing (A-02), compaction
(FR-07), statistics (FR-06), and every constraint-level input check
(C-04, C-05, C-06, C-08, FR-01, FR-02).

## Pro polish (beyond the spec)

The simulator ships with several extras designed to make it feel like
a real product, not a class demo:

* **Animated memory map** - rounded, shaded blocks that tween into their
  new positions with an ease-out cubic curve whenever the step changes.
* **Address ruler** with tick marks under every segment boundary.
* **Hover overlay** - other blocks dim, so the inspected block pops.
* **History sparkline** - live mini-chart of utilization vs. external
  fragmentation across the whole simulation.
* **Command palette** (Ctrl+K) - search-filter every action with
  keyboard shortcuts listed inline.
* **Undo / Redo** (Ctrl+Z / Ctrl+Y) - full process-list history with a
  50-step limit.
* **Random workload** generator - instantly produce a realistic test
  scenario that exposes fragmentation behaviour.
* **Export text report** (Ctrl+E) - writes a timestamped summary of the
  current memory map, stats, and step log.
* **Status bar** - live `Ready / Running / LIVE` indicator plus current
  metrics and a hint for Ctrl+K.

## Keyboard shortcuts

| Key                 | Action                |
| ------------------- | --------------------- |
| Ctrl+K              | Command palette       |
| Ctrl+R              | Run allocation        |
| Ctrl+Z              | Undo                  |
| Ctrl+Shift+Z / Ctrl+Y | Redo                |
| Ctrl+E              | Export text report    |
| Left                | Previous step         |
| Right               | Next step             |
| Space               | Play / Pause          |
| R                   | Restart simulation    |

## File map

```
OSPpy/
  memory_sim/
    model.py            # MemoryBlock, Process, MemoryManager
    algorithms.py       # First / Best / Worst / Next Fit + step generator
    theme.py            # Colour palette + ttk style configuration
    app.py              # Main window + controller
    views/
      control_panel.py       # Left column  - config + process form
      memory_map.py          # Center top   - animated rounded bar
      fragmentation_chart.py # Center       - history sparkline
      step_controls.py       # Center mid   - prev/next/play/speed
      step_log.py            # Center btm   - scrollable step log
      stats_panel.py         # Right top    - statistics + table
      educational.py         # Right btm    - algorithm explanations
      comparison.py          # Compare-dialog popup
      command_palette.py     # Ctrl+K modal
      status_bar.py          # Bottom status strip
      toast.py               # Auto-dismissing notification banner
  tests/
    test_model.py
    test_algorithms.py
  pyproject.toml
```

## Architecture (PDF 2.2)

Strict MVC separation:

* **Model** (`model.py`) - all memory state, invariants, and coalescing.
* **View** (`views/*.py`) - each widget is a self-contained `ttk.Frame`
  that only reads state handed to it via `set_state` / `update_state`.
* **Controller** (`app.py`) - subscribes to view callbacks, validates
  input, drives the step generator, and re-renders on every change.

## Out of scope (PDF 3.1)

Paging, segmentation, virtual memory, preemption, and save/load are
explicitly excluded in Phase 1 (C-01 .. C-03, C-07).
