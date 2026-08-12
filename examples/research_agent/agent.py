"""ResearchOps sample Python agent for adapter discovery.

The benchmark workload itself is described by workflow.yaml so prompts and
evaluation fixtures stay auditable. These functions demonstrate the Python
adapter boundary for future custom-agent integrations.
"""

from collections.abc import Callable
from typing import TypeVar

F = TypeVar("F", bound=Callable[..., object])


def a64forge_stage(function: F) -> F:
    return function


@a64forge_stage
def classify(request: str) -> str:
    """Classify a research request."""
    raise NotImplementedError("Executed through the configured local llama.cpp runtime")


@a64forge_stage
def extract(request: str) -> dict[str, str | None]:
    """Extract structured research constraints."""
    raise NotImplementedError("Executed through the configured local llama.cpp runtime")


@a64forge_stage
def tool_select(request: str) -> str:
    """Choose the deterministic local evidence tool."""
    raise NotImplementedError("Executed through the configured local llama.cpp runtime")


@a64forge_stage
def reason(evidence: str) -> str:
    """Reason over supplied evidence only."""
    raise NotImplementedError("Executed through the configured local llama.cpp runtime")


@a64forge_stage
def summarize(answer: str) -> str:
    """Produce a structured final summary."""
    raise NotImplementedError("Executed through the configured local llama.cpp runtime")

