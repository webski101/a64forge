from a64forge.benchmark.metrics import aggregate_latency, percentile


def test_percentile_interpolates() -> None:
    assert percentile([100, 200, 300], 0.95) == 290
    assert aggregate_latency([300, 100, 200]) == (200, 290)

