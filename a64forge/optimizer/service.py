from __future__ import annotations

import uuid
from collections.abc import Sequence

from a64forge.optimizer.pareto import frontier, group_by_stage
from a64forge.optimizer.scorer import score_records
from a64forge.schemas import (
    BenchmarkRecord,
    OptimizationResult,
    OptimizationStatus,
    RunLabel,
    StageRejection,
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
    rejections: list[StageRejection] = []
    baselines: list[BenchmarkRecord] = []
    records_by_stage = group_by_stage(records)
    for stage in workflow.stages:
        stage_id = stage.id
        stage_records = records_by_stage.get(stage_id, [])
        successful = [item for item in stage_records if not item.error and item.quality_score is not None]
        if not successful:
            rejections.append(
                StageRejection(
                    stage_id=stage_id,
                    quality_floor=workflow.minimum_quality,
                    reason="No successful measured candidates were available for this stage.",
                )
            )
            continue
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
            best = max(successful, key=lambda item: item.quality_score or 0)
            rejections.append(
                StageRejection(
                    stage_id=stage_id,
                    quality_floor=quality_floor,
                    best_candidate=best,
                    reason=(
                        f"Best measured quality {best.quality_score:.3f} did not meet "
                        f"the {quality_floor:.3f} quality floor."
                    ),
                )
            )
            continue
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
        status=(
            OptimizationStatus.NO_QUALIFYING_CANDIDATE
            if rejections
            else OptimizationStatus.DEPLOYABLE
        ),
        selections=selections,
        rejections=rejections,
        baseline=baselines,
        run_label=run_label,
    )
