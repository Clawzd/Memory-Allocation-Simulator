"""Allocation algorithms and step-trace generator.

Implements the four strategies mandated by PDF Section 2.3:

* First Fit  - first hole whose size >= request
* Best  Fit  - smallest hole whose size >= request
* Worst Fit  - largest available hole
* Next  Fit  - First Fit continuing from the last allocation cursor

Each strategy also produces a **scan trace** (ordered list of block ids
it inspected) so the GUI can animate the algorithm's search, mirroring
the website's ``scanning`` / ``scanning-fit`` step types in
``OS-Project/src/utils/memoryAllocator.js``.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Callable, Optional

from .model import MemoryBlock, MemoryManager, Process, validate_processes


class NoFitError(Exception):
    """Raised when no free hole is large enough to satisfy a request."""


@dataclass
class WorkloadEvent:
    """A single workload action.

    ``alloc`` events carry a Process. ``free`` events carry a process name.
    The simple public API still accepts ``list[Process]`` and treats every
    process as an allocation event.
    """

    op: str
    process: Optional[Process] = None
    process_name: Optional[str] = None

    @classmethod
    def alloc(cls, process: Process) -> "WorkloadEvent":
        return cls("alloc", process=process, process_name=process.name)

    @classmethod
    def free(cls, process_name: str) -> "WorkloadEvent":
        return cls("free", process_name=process_name)


# Result of a single search: (index_of_chosen_block, scanned_block_ids).
SearchResult = tuple[int, list[str]]


# ---------------------------------------------------------------------------
# Core strategies
# ---------------------------------------------------------------------------


def first_fit(blocks: list[MemoryBlock], size: int, cursor: int = 0) -> SearchResult:
    """Return the first free block whose size >= *size*."""
    scan: list[str] = []
    for i, b in enumerate(blocks):
        scan.append(b.id)
        if b.is_free and b.size >= size:
            return i, scan
    raise NoFitError(f"First-Fit: no hole \u2265 {size} available.")


def best_fit(blocks: list[MemoryBlock], size: int, cursor: int = 0) -> SearchResult:
    """Return the *smallest* free block whose size >= *size*."""
    scan: list[str] = []
    best_idx: Optional[int] = None
    best_size: Optional[int] = None
    for i, b in enumerate(blocks):
        scan.append(b.id)
        if b.is_free and b.size >= size:
            if best_size is None or b.size < best_size:
                best_idx = i
                best_size = b.size
    if best_idx is None:
        raise NoFitError(f"Best-Fit: no hole \u2265 {size} available.")
    return best_idx, scan


def worst_fit(blocks: list[MemoryBlock], size: int, cursor: int = 0) -> SearchResult:
    """Return the *largest* free block whose size >= *size*."""
    scan: list[str] = []
    worst_idx: Optional[int] = None
    worst_size: Optional[int] = None
    for i, b in enumerate(blocks):
        scan.append(b.id)
        if b.is_free and b.size >= size:
            if worst_size is None or b.size > worst_size:
                worst_idx = i
                worst_size = b.size
    if worst_idx is None:
        raise NoFitError(f"Worst-Fit: no hole \u2265 {size} available.")
    return worst_idx, scan


def next_fit(blocks: list[MemoryBlock], size: int, cursor: int = 0) -> SearchResult:
    """First-Fit variant that begins at *cursor* and wraps around."""
    n = len(blocks)
    if n == 0:
        raise NoFitError("Next-Fit: memory is empty.")
    start = cursor % n
    scan: list[str] = []
    for offset in range(n):
        i = (start + offset) % n
        b = blocks[i]
        scan.append(b.id)
        if b.is_free and b.size >= size:
            return i, scan
    raise NoFitError(f"Next-Fit: no hole \u2265 {size} available.")


AlgorithmFn = Callable[[list[MemoryBlock], int, int], SearchResult]

ALGORITHMS: dict[str, AlgorithmFn] = {
    "first-fit": first_fit,
    "best-fit": best_fit,
    "worst-fit": worst_fit,
    "next-fit": next_fit,
}


def pretty_name(key: str) -> str:
    return {
        "first-fit": "First Fit",
        "best-fit": "Best Fit",
        "worst-fit": "Worst Fit",
        "next-fit": "Next Fit",
    }.get(key, key)


# ---------------------------------------------------------------------------
# Step generation
# ---------------------------------------------------------------------------


def _snapshot(mm: MemoryManager) -> list[dict]:
    """Frozen projection of memory state used inside a step record."""
    return [b.to_dict() for b in deepcopy(mm.blocks)]


def _block_label(block: MemoryBlock) -> str:
    kind = "hole" if block.is_free else f"process {block.process_name}"
    return f"{kind} at {block.start_address}-{block.end_address} ({block.size} KB)"


def generate_allocation_steps(
    total_size: int,
    processes: list[Process],
    algorithm: str,
) -> list[dict]:
    """Compatibility wrapper for allocation-only workloads."""
    return generate_workload_steps(
        total_size, [WorkloadEvent.alloc(p) for p in processes], algorithm
    )


def generate_workload_steps(
    total_size: int,
    workload: list[WorkloadEvent],
    algorithm: str,
) -> list[dict]:
    """Simulate the full allocation sequence and return a list of step dicts.

    Each step has the shape::

        {
          "type":         "initial" | "considering" | "scanning"
                           | "scanning-fit" | "allocated" | "failed" | "done",
          "blocks":       [ block-dict, ... ],  # memory state AT this step
          "process_name": str | None,
          "scanning_block_id": str | None,      # currently-inspected block
          "message":      str,                  # human-readable log line
        }
    """
    if algorithm not in ALGORITHMS:
        raise ValueError(
            f"Unknown algorithm '{algorithm}'. "
            f"Expected one of: {', '.join(ALGORITHMS)}"
        )

    allocs = [e.process for e in workload if e.op == "alloc" and e.process]
    validate_processes(allocs, total_size)
    for event in workload:
        if event.op not in {"alloc", "free"}:
            raise ValueError(f"Unknown workload operation '{event.op}'.")
        if event.op == "free" and not (event.process_name or "").strip():
            raise ValueError("Free events must name a process.")
    _validate_workload_events(workload)

    mm = MemoryManager(total_size)
    strategy = ALGORITHMS[algorithm]
    steps: list[dict] = []

    steps.append(
        {
            "type": "initial",
            "blocks": _snapshot(mm),
            "process_name": None,
            "scanning_block_id": None,
            "message": (
                f"Initial memory: {total_size} KB free "
                f"(algorithm: {pretty_name(algorithm)})."
            ),
        }
    )

    for event in workload:
        if event.op == "free":
            name = (event.process_name or "").strip()
            steps.append(
                {
                    "type": "considering",
                    "blocks": _snapshot(mm),
                    "process_name": name,
                    "scanning_block_id": None,
                    "message": f"Free request: release {name}.",
                }
            )
            if mm.deallocate_by_name(name):
                steps.append(
                    {
                        "type": "deallocated",
                        "blocks": _snapshot(mm),
                        "process_name": name,
                        "scanning_block_id": None,
                        "message": (
                            f"{name} deallocated; adjacent free holes coalesced."
                        ),
                    }
                )
            else:
                steps.append(
                    {
                        "type": "failed",
                        "blocks": _snapshot(mm),
                        "process_name": name,
                        "scanning_block_id": None,
                        "message": f"{name}: free failed - process is not resident.",
                    }
                )
            continue

        proc = event.process
        if proc is None:
            raise ValueError("Allocation events must include a process.")
        steps.append(
            {
                "type": "considering",
                "blocks": _snapshot(mm),
                "process_name": proc.name,
                "scanning_block_id": None,
                "message": (
                    f"Next process: {proc.name} requesting {proc.size} KB."
                ),
            }
        )
        try:
            chosen_idx, scan_trace = strategy(
                mm.blocks, proc.size, mm.next_fit_cursor
            )
        except NoFitError as exc:
            steps.append(
                {
                    "type": "failed",
                    "blocks": _snapshot(mm),
                    "process_name": proc.name,
                    "scanning_block_id": None,
                    "message": (
                        f"{proc.name}: allocation failed - {exc} "
                        "(skipping, continuing simulation)."
                    ),
                }
            )
            continue

        # Emit a scanning step for every inspected block up to, but not
        # including, the chosen one. The chosen block gets a 'scanning-fit'
        # highlight so the UI can pulse it.
        chosen_id = mm.blocks[chosen_idx].id
        for bid in scan_trace[:-1]:
            scanned = next((b for b in mm.blocks if b.id == bid), None)
            label = _block_label(scanned) if scanned is not None else "memory block"
            steps.append(
                {
                    "type": "scanning",
                    "blocks": _snapshot(mm),
                    "process_name": proc.name,
                    "scanning_block_id": bid,
                    "message": f"Scanning {label} for {proc.name}.",
                }
            )
        steps.append(
            {
                "type": "scanning-fit",
                "blocks": _snapshot(mm),
                "process_name": proc.name,
                "scanning_block_id": chosen_id,
                "message": (
                    f"{pretty_name(algorithm)} chose block starting at "
                    f"{mm.blocks[chosen_idx].start_address} "
                    f"(size {mm.blocks[chosen_idx].size}) for {proc.name}."
                ),
            }
        )

        allocated = mm.place(chosen_idx, proc)
        steps.append(
            {
                "type": "allocated",
                "blocks": _snapshot(mm),
                "process_name": proc.name,
                "scanning_block_id": allocated.id,
                "message": (
                    f"{proc.name} allocated {proc.size} KB at address "
                    f"{allocated.start_address}-{allocated.end_address}."
                ),
            }
        )

    steps.append(
        {
            "type": "done",
            "blocks": _snapshot(mm),
            "process_name": None,
            "scanning_block_id": None,
            "message": "Simulation complete.",
        }
    )
    return steps


def _validate_workload_events(workload: list[WorkloadEvent]) -> None:
    """Validate event-level rules that plain Process validation cannot see."""
    allocated_names: set[str] = set()
    resident_names: set[str] = set()
    for event in workload:
        if event.op == "alloc":
            if event.process is None:
                raise ValueError("Allocation events must include a process.")
            name = event.process.name.strip()
            if name in allocated_names:
                raise ValueError(
                    f"Duplicate process name '{name}'. Process names must be unique."
                )
            allocated_names.add(name)
            resident_names.add(name)
            continue

        name = (event.process_name or "").strip()
        if name not in allocated_names:
            raise ValueError(f"Cannot free '{name}' before it is allocated.")
        if name not in resident_names:
            raise ValueError(f"Process '{name}' is already freed.")
        resident_names.remove(name)


# ---------------------------------------------------------------------------
# Comparison helper (FR-06-adjacent extra, mirrors Home.jsx handleCompare)
# ---------------------------------------------------------------------------


def compare_algorithms(total_size: int, processes: list[Process]) -> list[dict]:
    """Run all four strategies against the same allocation-only workload."""
    return compare_workload_algorithms(
        total_size, [WorkloadEvent.alloc(p) for p in processes]
    )


def compare_workload_algorithms(
    total_size: int,
    workload: list[WorkloadEvent],
) -> list[dict]:
    """Run all four strategies against the same workload, return summary rows."""
    results: list[dict] = []
    for key in ALGORITHMS:
        # fresh copy because generated Processes carry unique ids.
        events: list[WorkloadEvent] = []
        for event in workload:
            if event.op == "alloc" and event.process is not None:
                p = event.process
                events.append(
                    WorkloadEvent.alloc(Process(p.name, p.size, p.color_index))
                )
            elif event.op == "free":
                events.append(WorkloadEvent.free(event.process_name or ""))
        try:
            steps = generate_workload_steps(total_size, events, key)
        except Exception as exc:  # noqa: BLE001 - show to user
            results.append(
                {
                    "algorithm": key,
                    "label": pretty_name(key),
                    "error": str(exc),
                }
            )
            continue
        final_blocks = steps[-1]["blocks"]
        used = sum(b["size"] for b in final_blocks if not b["is_free"])
        free = total_size - used
        holes = [b for b in final_blocks if b["is_free"]]
        largest = max((b["size"] for b in holes), default=0)
        failed = sum(1 for s in steps if s["type"] == "failed")
        allocated = sum(1 for s in steps if s["type"] == "allocated")
        scanned = sum(
            1 for s in steps if s["type"] in {"scanning", "scanning-fit"}
        )
        results.append(
            {
                "algorithm": key,
                "label": pretty_name(key),
                "used": used,
                "free": free,
                "utilization": round(used / total_size * 100, 1) if total_size else 0.0,
                "holes": len(holes),
                "largest_free": largest,
                "allocated_processes": allocated,
                "failed_processes": failed,
                "scanned_blocks": scanned,
                "avg_scan": round(scanned / allocated, 1) if allocated else 0.0,
            }
        )
    return results
