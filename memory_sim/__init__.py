"""ICS 433 Memory Allocation Simulator - Tkinter edition.

Re-exports the main public API so callers can do
``from memory_sim import MemoryManager, Process``.
"""

from .model import MemoryBlock, MemoryManager, Process, unit_scale
from .algorithms import (
    ALGORITHMS,
    NoFitError,
    WorkloadEvent,
    best_fit,
    compare_algorithms,
    compare_workload_algorithms,
    first_fit,
    generate_allocation_steps,
    generate_workload_steps,
    next_fit,
    worst_fit,
)

__all__ = [
    "MemoryBlock",
    "MemoryManager",
    "Process",
    "unit_scale",
    "ALGORITHMS",
    "NoFitError",
    "WorkloadEvent",
    "best_fit",
    "first_fit",
    "next_fit",
    "worst_fit",
    "generate_allocation_steps",
    "generate_workload_steps",
    "compare_algorithms",
    "compare_workload_algorithms",
]
