from __future__ import annotations

from collections.abc import Sequence

from a64forge.schemas import BenchmarkRecord

WEIGHTS = {
    "balanced": {"latency": 0.35, "memory": 0.20, "throughput": 0.20, "quality": 0.25},
    "latency": {"latency": 0.70, "memory": 0.10, "throughput": 0.05, "quality": 0.15},
    "memory": {"latency": 0.10, "memory": 0.70, "throughput": 0.05, "quality": 0.15},
    "throughput": {"latency": 0.05, "memory": 0.10, "throughput": 0.70, "quality": 0.15},
    "quality": {"latency": 0.05, "memory": 0.05, "throughput": 0.05, "quality": 0.85},
}


def _normalize(value: float | None, values: list[float], maximize: bool) -> float:
    if value is None or not values:
        return 0.0
    low, high = min(values), max(values)
    if low == high:
        return 1.0
    unit = (value - low) / (high - low)
    return unit if maximize else 1 - unit


def score_records(records: Sequence[BenchmarkRecord], target: str) -> dict[int, float]:
    if target not in WEIGHTS:
        raise ValueError(f"Unknown optimization target {target!r}; choose {', '.join(WEIGHTS)}")
    latency = [item.median_latency_ms for item in records if item.median_latency_ms is not None]
    memory = [item.peak_memory_mb for item in records if item.peak_memory_mb is not None]
    throughput = [item.requests_per_minute for item in records if item.requests_per_minute is not None]
    quality = [item.quality_score for item in records if item.quality_score is not None]
    weights = WEIGHTS[target]
    return {
        id(item): round(
            weights["latency"] * _normalize(item.median_latency_ms, latency, False)
            + weights["memory"] * _normalize(item.peak_memory_mb, memory, False)
            + weights["throughput"] * _normalize(item.requests_per_minute, throughput, True)
            + weights["quality"] * _normalize(item.quality_score, quality, True),
            8,
        )
        for item in records
    }

