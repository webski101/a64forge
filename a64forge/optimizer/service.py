from __future__ import annotations

import uuid
from collections.abc import Sequence

from a64forge.optimizer.pareto import frontier, group_by_stage
from a64forge.optimizer.scorer import score_records
from a64forge.schemas import (
    BenchmarkRecord,
    OptimizationResult,
    RunLabel,
    StageSelection,
    WorkflowSpec,
)


def _percent_change(before: float | None, after: float | None, lower_is_better: bool) -> str | None:
    if before is None or after is None or before == 0:
        return None
    change = (before - after) / before * 100 if lower_is_better else (after - before) / before * 100
    return f"{change:.1f}% {'lower' if lower_is_better else 'higher'}"


def optimize_records(
    records: Sequence[BenchmarkRecord], workflow: WorkflowSpec, target: str = "balanced"
) -> OptimizationResult:
    if not records:
        raise ValueError("No benchmark records found. Run a64forge benchmark first.")
    selections: list[StageSelection] = []
    baselines: list[BenchmarkRecord] = []
    for stage_id, stage_records in group_by_stage(records).items():
        successful = [item for item in stage_records if not item.error and item.quality_score is not None]
        if not successful:
            raise ValueError(f"Stage {stage_id} has no successful measured candidates")
        explicit_baselines = [item for item in successful if item.metadata.get("baseline") is True]
        baseline = explicit_baselines[0] if explicit_baselines else max(
            successful, key=lambda item: item.quality_score or 0
        )
        baselines.append(baseline)
        quality_floor = max(
            workflow.minimum_quality,
            (baseline.quality_score or 0) - workflow.maximum_quality_drop,
        )
        eligible = [item for item in successful if (item.quality_score or 0) >= quality_floor]
        if not eligible:
            raise ValueError(
                f"Stage {stage_id} has no candidate meeting quality floor {quality_floor:.3f}"
            )
        pareto = frontier(eligible)
        scores = score_records(pareto, target)
        selected = max(pareto, key=lambda item: scores[id(item)])
        explanation = [
            f"Meets quality floor {quality_floor:.3f} with {selected.quality_score:.3f}.",
            f"Selected from {len(pareto)} Pareto-efficient candidates using the {target} preset.",
        ]
        latency_change = _percent_change(
            baseline.median_latency_ms, selected.median_latency_ms, lower_is_better=True
        )
        memory_change = _percent_change(
            baseline.peak_memory_mb, selected.peak_memory_mb, lower_is_better=True
        )
        if latency_change:
            explanation.append(f"Median latency: {latency_change} than baseline.")
        if memory_change:
            explanation.append(f"Peak memory: {memory_change} than baseline.")
        selections.append(
            StageSelection(
                stage_id=stage_id,
                target=target,
                selected=selected,
                pareto_keys=[
                    f"{item.model}:{item.quantization}:t{item.threads}:b{item.batch_size}:c{item.context_size}"
                    for item in pareto
                ],
                explanation=explanation,
                score=scores[id(selected)],
            )
        )
    labels = {item.run_label for item in records}
    run_label = labels.pop() if len(labels) == 1 else RunLabel.UNVERIFIED
    return OptimizationResult(
        optimization_id=f"opt-{uuid.uuid4().hex[:12]}",
        run_id=records[0].run_id,
        target=target,
        workflow=workflow.name,
        minimum_quality=workflow.minimum_quality,
        selections=selections,
        baseline=baselines,
        run_label=run_label,
    )
