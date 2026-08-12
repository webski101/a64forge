from a64forge.optimizer.pareto import dominates, frontier
from a64forge.optimizer.scorer import score_records
from a64forge.optimizer.service import optimize_records


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

