from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import Awaitable, Callable
from pathlib import Path

from a64forge.benchmark.matrix import (
    generate_coarse_matrix,
    generate_fine_matrix,
    select_diverse_coarse,
)
from a64forge.benchmark.runner import LlamaServerRunner
from a64forge.config import load_project_config, load_workflow
from a64forge.optimizer.compiler import compile_deployment
from a64forge.optimizer.pareto import frontier
from a64forge.optimizer.service import optimize_records
from a64forge.profiler.hardware import detect_hardware
from a64forge.report.generator import generate_report
from a64forge.schemas import BenchmarkCandidate, BenchmarkRecord, ProgressEvent, ProjectConfig
from a64forge.storage import EvidenceStore

EventSink = Callable[[ProgressEvent], Awaitable[None] | None]


def database_path() -> Path:
    import os

    return Path(os.getenv("A64FORGE_DB", ".a64forge/a64forge.db")).resolve()


async def run_benchmarks(
    config: ProjectConfig,
    store: EvidenceStore,
    event_sink: EventSink | None = None,
) -> list[BenchmarkRecord]:
    hardware = detect_hardware()
    workflow = load_workflow(config.workflow)
    run_id = f"run-{uuid.uuid4().hex[:12]}"
    matrix = generate_coarse_matrix(config)
    per_stage = max(1, config.search.max_candidates // len(workflow.stages))
    coarse_budget = max(1, (2 * per_stage + 2) // 3)
    baseline_model = next(item for item in config.models if item.id == config.baseline_model)
    baseline_variant = next(
        item for item in baseline_model.variants if item.quantization == config.baseline_quantization
    )
    baseline_candidate = BenchmarkCandidate(
        model_id=baseline_model.id,
        model_name=baseline_model.name,
        model_repo=baseline_model.repo,
        model_path=baseline_variant.path,
        quantization=baseline_variant.quantization,
        threads=config.baseline_threads,
        batch_size=config.baseline_batch_size,
        context_size=config.baseline_context_size,
    )
    coarse_candidates = select_diverse_coarse(
        matrix,
        baseline_candidate,
        coarse_budget,
    )
    runner = LlamaServerRunner(hardware, config.search, Path("benchmarks").resolve())
    records: list[BenchmarkRecord] = []
    started = time.monotonic()
    if event_sink:
        result = event_sink(
            ProgressEvent(event="start", message="Profiling host and validating runtime", progress=0)
        )
        if asyncio.iscoroutine(result):
            await result
    total = len(workflow.stages) * per_stage
    completed = 0

    async def measure(
        stage_id: str,
        candidate: BenchmarkCandidate,
        phase: str,
    ) -> BenchmarkRecord:
        nonlocal completed
        stage = next(item for item in workflow.stages if item.id == stage_id)
        if time.monotonic() - started > config.search.max_runtime_seconds:
            raise RuntimeError(
                f"Benchmark stopped at the {config.search.max_runtime_seconds}s safety limit"
            )
        record = await runner.run(run_id, stage, candidate, callback=event_sink)
        record.metadata["baseline"] = candidate.key == baseline_candidate.key
        record.metadata["search_phase"] = phase
        records.append(record)
        store.save_records([record])
        completed += 1
        if event_sink:
            result = event_sink(
                ProgressEvent(
                    event="progress",
                    message=f"Stored {completed}/{total} bounded candidate results",
                    stage_id=stage.id,
                    candidate_key=candidate.key,
                    progress=min(completed / total, 1),
                )
            )
            if asyncio.iscoroutine(result):
                await result
        return record

    for stage in workflow.stages:
        stage_records = [
            await measure(stage.id, candidate, "coarse")
            for candidate in coarse_candidates
        ]
        baseline_record = next(
            (item for item in stage_records if item.metadata.get("baseline")), None
        )
        baseline_quality = (
            baseline_record.quality_score
            if baseline_record and baseline_record.quality_score is not None
            else workflow.minimum_quality
        )
        quality_floor = max(
            workflow.minimum_quality,
            baseline_quality - workflow.maximum_quality_drop,
        )
        eligible = [
            item
            for item in stage_records
            if not item.error
            and item.quality_score is not None
            and item.quality_score >= quality_floor
        ]
        promising_keys = {
            (
                item.model,
                item.quantization,
                item.threads,
                item.batch_size,
                item.context_size,
            )
            for item in frontier(eligible)
        }
        promising = [
            candidate
            for candidate in coarse_candidates
            if (
                candidate.model_id,
                candidate.quantization,
                candidate.threads,
                candidate.batch_size,
                candidate.context_size,
            )
            in promising_keys
        ]
        fine_candidates = generate_fine_matrix(
            config,
            promising,
            per_stage - len(coarse_candidates),
        )
        coarse_keys = {item.key for item in coarse_candidates}
        for candidate in fine_candidates:
            if candidate.key not in coarse_keys:
                await measure(stage.id, candidate, "fine")
    if event_sink:
        result = event_sink(
            ProgressEvent(event="complete", message="Benchmark matrix complete", progress=1)
        )
        if asyncio.iscoroutine(result):
            await result
    return records


async def autopilot(config_path: Path | None = None, event_sink: EventSink | None = None) -> dict[str, object]:
    config = load_project_config(config_path)
    workflow = load_workflow(config.workflow)
    store = EvidenceStore(database_path())
    records = await run_benchmarks(config, store, event_sink)
    result = optimize_records(records, workflow, "balanced")
    store.save_optimization(result)
    compiled = compile_deployment(result, Path("dist").resolve())
    reports = generate_report(result, detect_hardware(), Path("reports").resolve())
    return {"run_id": result.run_id, "optimization_id": result.optimization_id, "compiled": compiled, "reports": reports}
