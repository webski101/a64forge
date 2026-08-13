from a64forge.optimizer.pareto import dominates, frontier
from a64forge.optimizer.scorer import score_records
from a64forge.optimizer.service import optimize_records, override_baseline
from a64forge.schemas import OptimizationStatus


def test_pareto_dominance(make_record) -> None:
    strong = make_record(latency=80, memory=400, throughput=80, quality=0.96)
    weak = make_record(latency=100, memory=500, throughput=60, quality=0.94)
    assert dominates(strong, weak)
    assert frontier([strong, weak]) == [strong]


def test_balanced_scoring_prefers_real_tradeoff(make_record) -> None:
    fast = make_record(latency=60, memory=600, throughput=100, quality=0.92)
    quality = make_record(model="large", latency=120, memory=900, throughput=40, quality=0.99)
    scores = score_records([fast, quality], "balanced")
    assert scores[id(fast)] > scores[id(quality)]


def test_quality_gate_and_explicit_baseline(make_record, sample_workflow) -> None:
    baseline = make_record(model="large", latency=150, memory=900, throughput=40, quality=0.96, baseline=True)
    winner = make_record(model="small", latency=70, memory=450, throughput=90, quality=0.95)
    invalid = make_record(model="tiny", latency=30, memory=200, throughput=160, quality=0.70)
    result = optimize_records([baseline, winner, invalid], sample_workflow, "balanced")
    assert result.baseline[0].model == "large"
    assert result.selections[0].selected.model == "small"
    assert result.status == OptimizationStatus.DEPLOYABLE
    assert result.rejections == []


def test_failed_quality_gate_returns_non_deployable_result(make_record, sample_workflow) -> None:
    baseline = make_record(model="large", quality=0.70, baseline=True)
    candidate = make_record(model="small", quality=0.80)

    result = optimize_records([baseline, candidate], sample_workflow)

    assert result.status == OptimizationStatus.NO_QUALIFYING_CANDIDATE
    assert result.deployable is False
    assert result.selections == []
    assert result.rejections[0].stage_id == "classify"
    assert result.rejections[0].best_candidate == candidate
    assert "0.800" in result.rejections[0].reason


def test_explanation_uses_higher_when_selected_latency_regresses(
    make_record, sample_workflow
) -> None:
    baseline = make_record(
        model="large", latency=100, memory=900, throughput=40, quality=0.95, baseline=True
    )
    slower = make_record(
        model="small", latency=150, memory=100, throughput=200, quality=0.99
    )

    result = optimize_records([baseline, slower], sample_workflow)

    explanation = result.selections[0].explanation
    assert "Median latency: 50.0% higher than baseline." in explanation


def test_override_baseline_uses_exact_measured_candidate(make_record) -> None:
    small = make_record(model="small")
    large = make_record(model="large")
    updated = override_baseline([small, large], "large:Q4_K_M:t4:b256:c2048")
    assert updated[0].metadata["baseline"] is False
    assert updated[1].metadata["baseline"] is True
    assert large.metadata["baseline"] is False
