from a64forge.benchmark.quality import exact_match, reference_coverage, structured_accuracy


def test_exact_match_normalizes_whitespace_and_case() -> None:
    assert exact_match("  Technical\n", "technical") == 1


def test_structured_accuracy_is_field_level() -> None:
    predicted = '```json\n{"topic":"Arm", "region":"Nigeria", "date":"wrong"}\n```'
    assert structured_accuracy(predicted, {"topic": "arm", "region": "Nigeria", "date": "2026"}) == 2 / 3


def test_reference_coverage_is_deterministic() -> None:
    assert reference_coverage("Config B uses 1450 MB and scores 0.94.", ["Config B", "1450 MB", "0.94"]) == 1

