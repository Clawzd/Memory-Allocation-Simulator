# Memory Allocation Simulator

**ICS 433 - Operating Systems | King Fahd University of Petroleum & Minerals**
**Final Delivery (Phase 3)**

An interactive desktop application that demonstrates how an operating system
manages contiguous physical memory. Users define a total memory size, queue
processes with specific size demands, choose one of four classic allocation
strategies (First Fit, Best Fit, Worst Fit, Next Fit), and watch the simulator
place those processes block by block. The memory map, live statistics, history
sparkline, and step-by-step replay all update in real time.

---

## Team

| Student ID | Name | Role |
| --- | --- | --- |
| 202280020 | Ali Alsarhayd     | Team Leader |
| 201948610 | Abdulkarim Althani | Team Member |
| 202039820 | Mohammed Alrasasi | Team Member |
| 202263680 | Hassan Alhassan   | Team Member |

---

## Requirements

- **Python 3.11 or newer**
- **Tkinter** (ships with the official Python installer on Windows and macOS;
  on most Linux distros it is a separate package).
- No external Python packages are required to run the simulator.
  `pytest` is needed only to execute the unit-test suite.

Install Tkinter on Linux if missing:

```bash
sudo apt install python3-tk        # Debian / Ubuntu
sudo dnf install python3-tkinter   # Fedora
```

---

## How to Run the Project

From the project root (the folder containing this README):

### Windows (PowerShell or CMD)

```powershell
python -m memory_sim
```

### macOS / Linux

```bash
python3 -m memory_sim
```

### Or install as a package (development / editable mode)

```bash
pip install -e .
memory-sim
```

If `python` is not recognized on Windows, install Python from
<https://www.python.org/downloads/windows/> with **"Add python.exe to PATH"**
checked during installation.

---

## How to Use the Simulator

1. Set the **Total Memory** value (KB or MB) in the left panel.
2. Choose an **Algorithm**: First Fit, Best Fit, Worst Fit, or Next Fit.
3. **Add processes** to the queue using the *Name / Size* form, or click
   **Random workload** to generate a realistic workload.
4. Press **Run Allocation**. The center panel animates each placement; the
   right panel updates statistics live.
5. Toggle **Step-by-step mode** to inspect every scan/decision the algorithm
   makes. Use **Prev / Next / Play** and the speed slider to control playback.
6. Use **Compact Memory** to coalesce all free space into one trailing block.
7. Use **Reset / New Session** to clear everything and start over.
8. Open the **Compare Algorithms** dialog to run the same workload under all
   four strategies and see the metrics side by side.

### Keyboard shortcuts

| Shortcut | Action |
| --- | --- |
| `Ctrl+K` | Command palette (search any action) |
| `Ctrl+Z` / `Ctrl+Y` | Undo / Redo (50-state history) |
| `Ctrl+E` | Export a timestamped text report |
| `Space` | Play / pause step mode |

---

## Running the Tests

```bash
python -m pytest tests/ -q
```

The pytest suite covers algorithm correctness (including Next-Fit
wrap-around), hole splitting, immediate coalescing (A-02), compaction
(FR-07), statistics (FR-06), and every constraint-level input check
(C-04, C-05, C-06, C-08).

---

## Feature Traceability (Phase 1 Functional Requirements)

| ID | Feature | Implementation |
| --- | --- | --- |
| FR-01 | Configure total memory (KB / MB) | `memory_sim/views/control_panel.py` |
| FR-02 | Add / remove processes | `memory_sim/views/control_panel.py` |
| FR-03 | First / Best / Worst / Next Fit | `memory_sim/algorithms.py` |
| FR-04 | Allocate and report failure | `memory_sim/app.py` &rarr; `_on_run` |
| FR-05 | Visual memory map with addresses | `memory_sim/views/memory_map.py` |
| FR-06 | Live statistics + process table | `memory_sim/views/stats_panel.py` |
| FR-07 | Compact memory | `memory_sim/model.py` &rarr; `compact` |
| FR-08 | Reset / new session | `memory_sim/app.py` &rarr; `_on_reset` |
| FR-09 | Step-by-step mode | `memory_sim/views/step_controls.py` |

---

## Project Layout

```
Memory-Allocation-Simulator/
├── memory_sim/
│   ├── model.py                 # MemoryBlock, Process, MemoryManager
│   ├── algorithms.py            # First / Best / Worst / Next Fit + step generator
│   ├── theme.py                 # Cross-platform palette & ttk styles
│   ├── app.py                   # Main window + controller
│   └── views/
│       ├── control_panel.py
│       ├── memory_map.py
│       ├── fragmentation_chart.py
│       ├── step_controls.py
│       ├── step_log.py
│       ├── stats_panel.py
│       ├── educational.py
│       ├── comparison.py
│       ├── command_palette.py
│       ├── status_bar.py
│       └── toast.py
├── tests/
│   ├── test_model.py
│   └── test_algorithms.py
├── pyproject.toml
├── README.md
├── ICS433_Phase1_MemoryAllocationSimulator.pdf
├── ICS433_Phase2_MemoryAllocationSimulator.pdf
└── ICS433_Phase3_MemoryAllocationSimulator.pdf   # final report
```

---

## Architecture

Strict Model-View-Controller separation:

- **Model** (`model.py`, `algorithms.py`) - all memory state, invariants
  (immediate coalescing, split on allocate, compaction), and the four
  allocation strategies as pure functions and as event-emitting generators.
- **View** (`views/*.py`) - each widget is a self-contained `ttk.Frame` that
  receives state via `set_state` / `update_state` and never reads from the
  model directly.
- **Controller** (`app.py`) - validates input against the Phase 1 constraints
  (C-04..C-08), drives the step generator, owns the undo/redo stack, dispatches
  keyboard shortcuts, and pushes state to the views.

---

## Out of Scope

Paging, segmentation, virtual memory, preemption, and persistent
save/load are explicitly excluded by the Phase 1 constraints
(C-01..C-03, C-07).

---

## License

Coursework submission for ICS 433 (KFUPM). Not licensed for redistribution.
