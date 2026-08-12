from __future__ import annotations

import itertools
from collections.abc import Iterable

from a64forge.schemas import BenchmarkCandidate, ProjectConfig


def _spread(values: list[int]) -> list[int]:
    """Keep extrema and a center value for an informative coarse pass."""
    if len(values) <= 3:
        return values
    return sorted({values[0], values[len(values) // 2], values[-1]})


def generate_coarse_matrix(config: ProjectConfig) -> list[BenchmarkCandidate]:
    threads = _spread(config.search.threads)
    batches = _spread(config.search.batch_sizes)
    contexts = _spread(config.search.context_sizes)
    candidates: list[BenchmarkCandidate] = []
    for model in config.models:
        for variant, thread, batch, context in itertools.product(
            model.variants, threads, batches, contexts
        ):
            candidates.append(
                BenchmarkCandidate(
                    model_id=model.id,
                    model_name=model.name,
                    model_repo=model.repo,
                    model_path=variant.path,
                    quantization=variant.quantization,
                    threads=thread,
                    batch_size=batch,
                    context_size=context,
                )
            )
    # Interleave models and keep a deterministic, bounded Latin-hypercube-like sample.
    candidates.sort(key=lambda item: (item.threads, item.batch_size, item.context_size, item.model_id))
    if len(candidates) <= config.search.max_candidates:
        return candidates
    stride = len(candidates) / config.search.max_candidates
    return [candidates[int(index * stride)] for index in range(config.search.max_candidates)]


def select_diverse_coarse(
    candidates: Iterable[BenchmarkCandidate],
    baseline: BenchmarkCandidate,
    limit: int,
) -> list[BenchmarkCandidate]:
    """Prefer distinct model/quantization pairs before runtime-only variants."""
    if limit <= 1:
        return [baseline]
    pool = list(candidates)
    selected = {baseline.key: baseline}
    variants = {(baseline.model_id, baseline.quantization)}
    for candidate in pool:
        variant = (candidate.model_id, candidate.quantization)
        if variant in variants:
            continue
        selected[candidate.key] = candidate
        variants.add(variant)
        if len(selected) >= limit:
            return list(selected.values())
    for candidate in pool:
        selected.setdefault(candidate.key, candidate)
        if len(selected) >= limit:
            break
    return list(selected.values())


def generate_fine_matrix(
    config: ProjectConfig,
    promising: Iterable[BenchmarkCandidate],
    remaining: int,
) -> list[BenchmarkCandidate]:
    if remaining <= 0:
        return []
    seeds = list(promising)
    seed_keys = {item.key for item in seeds}
    threads = config.search.threads
    batches = config.search.batch_sizes
    contexts = config.search.context_sizes
    fine: dict[str, BenchmarkCandidate] = {}
    for winner in seeds:
        for values, current in (
            (threads, winner.threads),
            (batches, winner.batch_size),
            (contexts, winner.context_size),
        ):
            index = values.index(current) if current in values else 0
            neighbors = values[max(0, index - 1) : index + 2]
            for neighbor in neighbors:
                update = winner.model_copy(deep=True)
                if values is threads:
                    update.threads = neighbor
                elif values is batches:
                    update.batch_size = neighbor
                else:
                    update.context_size = neighbor
                fine[update.key] = update
    return [
        item
        for key, item in sorted(fine.items())
        if key not in seed_keys
    ][:remaining]
