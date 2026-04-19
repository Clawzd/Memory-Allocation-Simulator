"""Model layer for the Memory Allocation Simulator.

Implements the data structures required by Phase 1 of the ICS 433 spec
(Section 2.4). The simulator models a single flat physical memory as a
linked list of :class:`MemoryBlock` segments which are either allocated
to a process or free (a "hole").

Constraints enforced here (PDF Section 3.1):

* C-04 Integer Memory Units
* C-05 Maximum memory size = 1,000,000 units
* C-06 Maximum 100 concurrent processes
* C-08 No single process may exceed total memory

Adjacent free holes are automatically coalesced after every deallocation
(PDF A-02).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional
import itertools
import uuid

# ---------------------------------------------------------------------------
# Limits (PDF constraints)
# ---------------------------------------------------------------------------

MAX_MEMORY_SIZE = 1_000_000  # C-05
MAX_PROCESSES = 100          # C-06


def unit_scale(unit: str) -> int:
    """Return the KB multiplier for a UI memory unit."""
    return 1024 if str(unit).upper() == "MB" else 1


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


def _uid() -> str:
    return uuid.uuid4().hex[:8]


@dataclass
class MemoryBlock:
    """A contiguous memory segment (PDF Section 2.4)."""

    start_address: int
    size: int
    is_free: bool = True
    process_id: Optional[str] = None
    process_name: Optional[str] = None
    color_index: int = 0
    id: str = field(default_factory=_uid)

    @property
    def end_address(self) -> int:
        """Last byte address occupied by this block (inclusive)."""
        return self.start_address + self.size - 1

    @property
    def type(self) -> str:
        return "free" if self.is_free else "process"

    def to_dict(self) -> dict:
        """Plain-dict projection used by the view layer."""
        return {
            "id": self.id,
            "start": self.start_address,
            "end": self.end_address,
            "size": self.size,
            "type": self.type,
            "is_free": self.is_free,
            "process_id": self.process_id,
            "name": self.process_name,
            "color_index": self.color_index,
        }


@dataclass
class Process:
    """A user-defined process with a memory demand (PDF FR-02)."""

    name: str
    size: int
    color_index: int = 0
    id: str = field(default_factory=_uid)


# ---------------------------------------------------------------------------
# Memory manager
# ---------------------------------------------------------------------------


class MemoryManager:
    """The canonical representation of memory state.

    The manager owns an ordered list of :class:`MemoryBlock` segments that
    together tile the address range ``[0, total_size)``.
    """

    def __init__(self, total_size: int) -> None:
        self._validate_total(total_size)
        self.total_size: int = int(total_size)
        self.blocks: list[MemoryBlock] = [MemoryBlock(0, self.total_size, True)]
        # Cursor for the Next-Fit algorithm (PDF Section 2.3).
        self.next_fit_cursor: int = 0

    # -- validation ---------------------------------------------------------

    @staticmethod
    def _validate_total(total_size: int) -> None:
        if not isinstance(total_size, int) or isinstance(total_size, bool):
            raise ValueError("Total memory must be an integer (C-04).")
        if total_size <= 0:
            raise ValueError("Total memory must be > 0 (FR-01).")
        if total_size > MAX_MEMORY_SIZE:
            raise ValueError(
                f"Total memory must be \u2264 {MAX_MEMORY_SIZE} (C-05)."
            )

    # -- queries ------------------------------------------------------------

    def processes(self) -> list[MemoryBlock]:
        """Return a shallow copy of the allocated blocks only."""
        return [b for b in self.blocks if not b.is_free]

    def holes(self) -> list[MemoryBlock]:
        return [b for b in self.blocks if b.is_free]

    def has_process(self, process_id: str) -> bool:
        return any(b.process_id == process_id for b in self.blocks)

    # -- mutators -----------------------------------------------------------

    def reset(self) -> None:
        """Clear all processes and return memory to the empty state (FR-08)."""
        self.blocks = [MemoryBlock(0, self.total_size, True)]
        self.next_fit_cursor = 0

    def place(self, block_index: int, process: Process) -> MemoryBlock:
        """Place *process* inside the block at *block_index*.

        The block must be free and large enough. If it is larger than the
        request the remainder stays behind as a smaller free hole (PDF
        Section 2.3 - "split the hole").
        Returns the resulting **allocated** MemoryBlock.
        """
        block = self.blocks[block_index]
        if not block.is_free:
            raise ValueError("Target block is not free.")
        if block.size < process.size:
            raise ValueError("Target block is too small for the process.")
        if process.size <= 0:
            raise ValueError("Process size must be > 0 (FR-02).")
        if process.size > self.total_size:
            raise ValueError("Process exceeds total memory (C-08).")

        allocated = MemoryBlock(
            start_address=block.start_address,
            size=process.size,
            is_free=False,
            process_id=process.id,
            process_name=process.name,
            color_index=process.color_index,
        )
        remainder_size = block.size - process.size
        replacement: list[MemoryBlock] = [allocated]
        if remainder_size > 0:
            replacement.append(
                MemoryBlock(
                    start_address=block.start_address + process.size,
                    size=remainder_size,
                    is_free=True,
                )
            )
        self.blocks[block_index : block_index + 1] = replacement

        # Advance the Next-Fit cursor just past the newly allocated block.
        # Its new index is ``block_index`` (since allocated replaced it); the
        # next search should continue from the block after it.
        self.next_fit_cursor = block_index + 1

        return allocated

    def deallocate(self, process_id: str) -> bool:
        """Release the memory held by *process_id* (PDF FR-02).

        Returns True on success, False if the process is not resident.
        Adjacent free holes are immediately coalesced (PDF A-02).
        """
        for block in self.blocks:
            if block.process_id == process_id:
                block.is_free = True
                block.process_id = None
                block.process_name = None
                block.color_index = 0
                self._coalesce()
                return True
        return False

    def deallocate_by_name(self, name: str) -> bool:
        """Convenience: deallocate the first block whose name == *name*."""
        for block in self.blocks:
            if not block.is_free and block.process_name == name:
                return self.deallocate(block.process_id)  # type: ignore[arg-type]
        return False

    def compact(self) -> None:
        """Pack every allocated block to low addresses (PDF FR-07).

        All free holes are merged into a single trailing block.
        """
        cursor = 0
        new_blocks: list[MemoryBlock] = []
        free_total = 0
        for b in self.blocks:
            if b.is_free:
                free_total += b.size
                continue
            b.start_address = cursor
            cursor += b.size
            new_blocks.append(b)
        if free_total > 0:
            new_blocks.append(MemoryBlock(cursor, free_total, True))
        self.blocks = new_blocks
        self.next_fit_cursor = 0

    # -- internals ----------------------------------------------------------

    def _coalesce(self) -> None:
        """Merge adjacent free blocks (PDF A-02)."""
        merged: list[MemoryBlock] = []
        for b in self.blocks:
            if merged and merged[-1].is_free and b.is_free:
                merged[-1].size += b.size
            else:
                merged.append(b)
        self.blocks = merged

    # -- statistics (PDF FR-06) --------------------------------------------

    def stats(self) -> dict:
        used = sum(b.size for b in self.blocks if not b.is_free)
        free = self.total_size - used
        holes = [b for b in self.blocks if b.is_free]
        largest_free = max((b.size for b in holes), default=0)
        util = (used / self.total_size * 100) if self.total_size else 0.0
        # External fragmentation: portion of free space *not* in the largest hole.
        if free > 0:
            ext_frag = (free - largest_free) / free * 100
        else:
            ext_frag = 0.0
        return {
            "total": self.total_size,
            "used": used,
            "free": free,
            "used_percent": round(util, 1),
            "free_percent": round(100 - util, 1),
            "num_holes": len(holes),
            "largest_free": largest_free,
            "external_fragmentation": round(ext_frag, 1),
            "utilization": round(util, 1),
            "process_count": sum(1 for b in self.blocks if not b.is_free),
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def validate_processes(processes: Iterable[Process], total_size: int) -> None:
    """Raise ValueError if the process list violates PDF constraints."""
    procs = list(processes)
    if len(procs) > MAX_PROCESSES:
        raise ValueError(
            f"Too many processes (max {MAX_PROCESSES} per session, C-06)."
        )
    seen_ids: set[str] = set()
    for p in procs:
        if not p.name or not str(p.name).strip():
            raise ValueError("Every process must have a non-empty name (FR-02).")
        if not isinstance(p.size, int) or isinstance(p.size, bool):
            raise ValueError("Process size must be an integer (C-04).")
        if p.size <= 0:
            raise ValueError(f"Process '{p.name}' size must be > 0 (FR-02).")
        if p.size > total_size:
            raise ValueError(
                f"Process '{p.name}' ({p.size}) exceeds total memory (C-08)."
            )
        if p.id in seen_ids:
            raise ValueError("Duplicate process id detected.")
        seen_ids.add(p.id)


_color_counter = itertools.count()


def next_color_index() -> int:
    """Cycle through the palette defined in :mod:`memory_sim.theme`."""
    return next(_color_counter)
