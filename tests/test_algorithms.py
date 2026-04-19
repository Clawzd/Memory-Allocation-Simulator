"""Tests for the four allocation algorithms (PDF Section 2.3)."""

import pytest

from memory_sim import (
    MemoryManager, Process,
    first_fit, best_fit, worst_fit, next_fit,
    generate_allocation_steps, generate_workload_steps,
    WorkloadEvent, NoFitError,
)


def _setup_holes():
    """Memory layout:  [A(20)] [hole(30)] [B(10)] [hole(100)] [hole(40)]."""
    mm = MemoryManager(200)
    # carve out A at 0..19 and B at 50..59 manually for deterministic holes
    mm.place(0, Process("A", 20))       # blocks: [A20][180 free]
    # next-fit cursor now past A
    # place 30 hole + B10 by first-fitting a 30-sized block and freeing it
    idx, _ = first_fit(mm.blocks, 30)
    ph = Process("PH", 30)
    mm.place(idx, ph)                   # [A20][PH30][150 free]
    idx, _ = first_fit(mm.blocks, 10)
    mm.place(idx, Process("B", 10))     # [A20][PH30][B10][140 free]
    # split tail into two holes by placing + freeing at 100
    idx, _ = first_fit(mm.blocks, 100)
    filler = Process("F", 100)
    mm.place(idx, filler)               # [A20][PH30][B10][F100][40 free]
    mm.deallocate(ph.id)                # [A20][30 free][B10][F100][40 free]
    mm.deallocate(filler.id)            # [A20][30 free][B10][100 free][40 free]
    # coalesce may merge 100+40 -> [A20][30 free][B10][140 free]
    return mm


def test_first_fit_picks_first_hole():
    mm = _setup_holes()
    idx, scan = first_fit(mm.blocks, 25)
    # 30-byte hole is at index 1
    assert idx == 1
    assert mm.blocks[idx].is_free and mm.blocks[idx].size == 30


def test_best_fit_picks_smallest_suitable():
    mm = _setup_holes()
    idx, _ = best_fit(mm.blocks, 25)
    # Holes: 30 and 140. 30 is the tightest fit for 25.
    assert mm.blocks[idx].size == 30


def test_worst_fit_picks_largest():
    mm = _setup_holes()
    idx, _ = worst_fit(mm.blocks, 25)
    assert mm.blocks[idx].size == 140


def test_next_fit_wraps_around():
    mm = MemoryManager(100)
    mm.place(0, Process("A", 30))   # cursor -> 1 (points to free tail)
    mm.place(1, Process("B", 30))   # cursor -> 2 (points to free tail)
    mm.deallocate_by_name("A")      # free hole at index 0
    # Cursor is past index 1, but only free hole is at 0 -> must wrap.
    idx, _ = next_fit(mm.blocks, 20, cursor=mm.next_fit_cursor)
    assert mm.blocks[idx].is_free


def test_no_fit_raises():
    mm = MemoryManager(50)
    with pytest.raises(NoFitError):
        first_fit(mm.blocks, 100)


def test_generate_allocation_steps_has_required_types():
    procs = [Process("P1", 100), Process("P2", 200)]
    steps = generate_allocation_steps(512, procs, "first-fit")
    types = {s["type"] for s in steps}
    assert {"initial", "considering", "allocated", "done"}.issubset(types)
    assert steps[0]["type"] == "initial"
    assert steps[-1]["type"] == "done"


def test_generate_allocation_steps_reports_failure_gracefully():
    procs = [Process("TooBig", 400), Process("OK", 100)]
    # "TooBig" fits in 512, but fill memory first to force OK to fail.
    procs = [Process("Fill", 500), Process("OK", 100)]
    steps = generate_allocation_steps(512, procs, "first-fit")
    assert any(s["type"] == "failed" for s in steps)
    # simulation continues after failure
    assert steps[-1]["type"] == "done"


def test_workload_steps_can_deallocate_and_fragment_memory():
    workload = [
        WorkloadEvent.alloc(Process("P1", 100)),
        WorkloadEvent.alloc(Process("P2", 120)),
        WorkloadEvent.alloc(Process("P3", 80)),
        WorkloadEvent.free("P2"),
        WorkloadEvent.alloc(Process("P4", 60)),
    ]

    steps = generate_workload_steps(512, workload, "first-fit")

    assert any(s["type"] == "deallocated" for s in steps)
    final_blocks = steps[-1]["blocks"]
    holes = [b for b in final_blocks if b["is_free"]]
    assert len(holes) == 2
    assert any(b["name"] == "P4" and b["start"] == 100 for b in final_blocks)


def test_workload_comparison_can_distinguish_best_and_worst_fit():
    workload = [
        WorkloadEvent.alloc(Process("P1", 100)),
        WorkloadEvent.alloc(Process("P2", 120)),
        WorkloadEvent.alloc(Process("P3", 80)),
        WorkloadEvent.alloc(Process("P4", 100)),
        WorkloadEvent.free("P2"),
        WorkloadEvent.free("P4"),
        WorkloadEvent.alloc(Process("P5", 70)),
    ]

    best = generate_workload_steps(512, workload, "best-fit")[-1]["blocks"]
    worst = generate_workload_steps(512, workload, "worst-fit")[-1]["blocks"]

    best_p5 = next(b for b in best if b.get("name") == "P5")
    worst_p5 = next(b for b in worst if b.get("name") == "P5")
    assert best_p5["start"] == 100
    assert worst_p5["start"] == 300


def test_workload_rejects_duplicate_process_names():
    workload = [
        WorkloadEvent.alloc(Process("P1", 100)),
        WorkloadEvent.alloc(Process("P1", 50)),
    ]

    with pytest.raises(ValueError, match="Duplicate process name"):
        generate_workload_steps(512, workload, "first-fit")


def test_workload_rejects_repeated_free():
    workload = [
        WorkloadEvent.alloc(Process("P1", 100)),
        WorkloadEvent.free("P1"),
        WorkloadEvent.free("P1"),
    ]

    with pytest.raises(ValueError, match="already freed"):
        generate_workload_steps(512, workload, "first-fit")


def test_workload_rejects_free_before_alloc():
    workload = [WorkloadEvent.free("P1")]

    with pytest.raises(ValueError, match="before it is allocated"):
        generate_workload_steps(512, workload, "first-fit")
