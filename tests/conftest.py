from __future__ import annotations

from pathlib import Path

import pytest

from a64forge.schemas import BenchmarkRecord, RunLabel


@pytest.fixture
def make_record():
    def factory(
        stage: str = "classify",
        model: str = "small",
        latency: float = 100.0,
        memory: float = 500.0,
        throughput: float = 60.0,
        quality: float = 0.95,
        baseline: bool = False,
    ) -> BenchmarkRecord:
        return BenchmarkRecord(
            run_id="demo-test",
            git_commit="abc123",
            hostname="fixture-host",
            architecture="x86_64",
            cpu="FIXTURE CPU",
            cores=8,
            ram_gb=16,
            stage_id=stage,
            model=model,
            model_repo=f"fixture/{model}",
            model_hash="0" * 64,
            quantization="Q4_K_M",
            threads=4,
            batch_size=256,
            context_size=2048,
            median_latency_ms=latency,
            p95_latency_ms=latency * 1.1,
            requests_per_minute=throughput,
            peak_memory_mb=memory,
            quality_score=quality,
            measured_runs=3,
            warmup_runs=1,
            run_label=RunLabel.DEVELOPMENT,
            verified_arm64=False,
            dataset_hash="1" * 64,
            metadata={"baseline": baseline},
        )

    return factory


@pytest.fixture
def sample_workflow(tmp_path: Path):
    from a64forge.schemas import WorkflowSpec, WorkflowStage

    dataset = tmp_path / "data.jsonl"
    dataset.write_text('{"input":"x","expected":"x"}\n', encoding="utf-8")
    return WorkflowSpec(
        name="test-workflow",
        minimum_quality=0.9,
        maximum_quality_drop=0.02,
        stages=[
            WorkflowStage(
                id="classify",
                type="classification",
                prompt="Return a label.",
                quality_metric="exact_match",
                dataset=dataset,
            )
        ],
    )

