from __future__ import annotations

from collections.abc import Sequence
from typing import TypeVar

from a64forge.schemas import BenchmarkRecord

T = TypeVar("T")


def dominates(a: BenchmarkRecord, b: BenchmarkRecord) -> bool:
    """Return true when A is no worse on every objective and better on one."""
    objectives: list[tuple[float | None, float | None, bool]] = [
        (a.median_latency_ms, b.median_latency_ms, False),
        (a.peak_memory_mb, b.peak_memory_mb, False),
        (a.requests_per_minute, b.requests_per_minute, True),
        (a.quality_score, b.quality_score, True),
    ]
    comparable = [(x, y, maximize) for x, y, maximize in objectives if x is not None and y is not None]
    if not comparable:
        return False
    no_worse = all(x >= y if maximize else x <= y for x, y, maximize in comparable)
    strictly_better = any(x > y if maximize else x < y for x, y, maximize in comparable)
    return no_worse and strictly_better


def frontier(records: Sequence[BenchmarkRecord]) -> list[BenchmarkRecord]:
    valid = [item for item in records if not item.error]
    return [item for item in valid if not any(dominates(other, item) for other in valid if other is not item)]


def group_by_stage(records: Sequence[BenchmarkRecord]) -> dict[str, list[BenchmarkRecord]]:
    grouped: dict[str, list[BenchmarkRecord]] = {}
    for record in records:
        grouped.setdefault(record.stage_id, []).append(record)
    return grouped

