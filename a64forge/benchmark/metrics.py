from __future__ import annotations

import math
import statistics
from collections.abc import Sequence


def percentile(values: Sequence[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * quantile
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (rank - lower)


def aggregate_latency(values: Sequence[float]) -> tuple[float | None, float | None]:
    if not values:
        return None, None
    return statistics.median(values), percentile(values, 0.95)


def mean(values: Sequence[float]) -> float | None:
    return statistics.fmean(values) if values else None

