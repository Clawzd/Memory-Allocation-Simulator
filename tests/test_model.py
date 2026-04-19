"""Tests for the MemoryManager model (PDF Section 2.4)."""

import pytest

from memory_sim import MemoryManager, Process
from memory_sim.model import MAX_MEMORY_SIZE, unit_scale, validate_processes
from memory_sim.algorithms import first_fit


def test_initial_state():
    mm = MemoryManager(100)
    assert mm.total_size == 100
    assert len(mm.blocks) == 1
    assert mm.blocks[0].is_free
    assert mm.blocks[0].size == 100


@pytest.mark.parametrize("bad", [0, -1, MAX_MEMORY_SIZE + 1])
def test_invalid_totals(bad):
    with pytest.raises(ValueError):
        MemoryManager(bad)


def test_place_splits_hole():
    mm = MemoryManager(100)
    mm.place(0, Process("A", 40))
    assert [b.size for b in mm.blocks] == [40, 60]
    assert mm.blocks[0].process_name == "A"
    assert mm.blocks[1].is_free


def test_deallocate_coalesces():
    mm = MemoryManager(100)
    a = Process("A", 30); b = Process("B", 30); c = Process("C", 30)
    for p in (a, b, c):
        idx, _ = first_fit(mm.blocks, p.size)
        mm.place(idx, p)
    mm.deallocate(b.id)
    # Middle hole stays separate (A | hole | C | tail)
    assert sum(1 for blk in mm.blocks if blk.is_free) == 2
    mm.deallocate(a.id)
    # Leading hole merges with middle hole
    assert sum(1 for blk in mm.blocks if blk.is_free) == 2  # front-merged + tail
    mm.deallocate(c.id)
    # All gone -> single free block of full size
    assert len(mm.blocks) == 1
    assert mm.blocks[0].size == 100


def test_compact_collapses_holes():
    mm = MemoryManager(200)
    procs = [Process("A", 30), Process("B", 40), Process("C", 50)]
    for p in procs:
        idx, _ = first_fit(mm.blocks, p.size)
        mm.place(idx, p)
    mm.deallocate(procs[1].id)   # free the middle one
    mm.compact()
    assert [b.size for b in mm.blocks[:-1]] == [30, 50]  # packed together
    assert mm.blocks[-1].is_free and mm.blocks[-1].size == 200 - 80


def test_stats_shape():
    mm = MemoryManager(100)
    mm.place(0, Process("A", 25))
    s = mm.stats()
    assert s["total"] == 100 and s["used"] == 25 and s["free"] == 75
    assert s["num_holes"] == 1
    assert s["utilization"] == 25.0


def test_validate_processes_constraints():
    with pytest.raises(ValueError):
        validate_processes([Process("", 10)], 100)
    with pytest.raises(ValueError):
        validate_processes([Process("A", 0)], 100)
    with pytest.raises(ValueError):
        validate_processes([Process("A", 200)], 100)
    # Too many processes
    with pytest.raises(ValueError):
        validate_processes([Process(f"P{i}", 1) for i in range(101)], 10_000)


def test_unit_scale_matches_ui_memory_units():
    assert unit_scale("KB") == 1
    assert unit_scale("MB") == 1024
    assert unit_scale("mb") == 1024
