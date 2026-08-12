from __future__ import annotations

import json
import re
from collections.abc import Iterable
from typing import Any


def _normalize(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value).strip().lower())


def extract_json(value: str) -> Any | None:
    text = value.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if fenced:
        text = fenced.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"(?:\{.*\}|\[.*\])", text, re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None


def exact_match(predicted: str, expected: Any) -> float:
    return float(_normalize(predicted) == _normalize(expected))


def structured_accuracy(predicted: str, expected: dict[str, Any]) -> float:
    actual = extract_json(predicted)
    if not isinstance(actual, dict) or not expected:
        return 0.0
    matches = sum(_normalize(actual.get(key, "")) == _normalize(value) for key, value in expected.items())
    return matches / len(expected)


def reference_coverage(predicted: str, expected: Iterable[str]) -> float:
    facts = [_normalize(item) for item in expected]
    if not facts:
        return 1.0
    normalized = _normalize(predicted)
    return sum(fact in normalized for fact in facts) / len(facts)


def score_output(metric: str, predicted: str, expected: Any) -> float:
    if metric in {"exact_match", "tool_accuracy"}:
        if isinstance(expected, dict):
            expected = expected.get("label", expected.get("tool", expected))
        return exact_match(predicted, expected)
    if metric == "structured_accuracy":
        return structured_accuracy(predicted, expected)
    if metric in {"reference_coverage", "factual_coverage"}:
        facts = expected.get("facts", []) if isinstance(expected, dict) else expected
        return reference_coverage(predicted, facts)
    raise ValueError(f"Unsupported quality metric: {metric}")

