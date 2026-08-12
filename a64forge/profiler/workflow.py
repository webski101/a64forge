from __future__ import annotations

import ast
from pathlib import Path
from typing import Protocol

from a64forge.config import load_workflow
from a64forge.schemas import WorkflowSpec, WorkflowStage


class WorkflowAdapter(Protocol):
    def can_handle(self, path: Path) -> bool: ...
    def analyze(self, path: Path) -> WorkflowSpec: ...


class YamlWorkflowAdapter:
    def can_handle(self, path: Path) -> bool:
        return path.suffix.lower() in {".yaml", ".yml"}

    def analyze(self, path: Path) -> WorkflowSpec:
        return load_workflow(path)


class PythonAgentAdapter:
    """Conservative adapter for sample/custom agents with decorated stage functions."""

    def can_handle(self, path: Path) -> bool:
        return path.suffix.lower() == ".py"

    def analyze(self, path: Path) -> WorkflowSpec:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        stages: list[WorkflowStage] = []
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            decorator_names: set[str] = set()
            for item in node.decorator_list:
                if isinstance(item, ast.Name):
                    decorator_names.add(item.id)
                elif isinstance(item, ast.Call) and isinstance(item.func, ast.Name):
                    decorator_names.add(item.func.id)
            if "a64forge_stage" not in decorator_names:
                continue
            stages.append(
                WorkflowStage(
                    id=node.name,
                    type="custom",
                    prompt=ast.get_docstring(node) or f"Execute stage {node.name}.",
                    quality_metric="reference_coverage",
                    dataset=path.with_name(f"{node.name}.jsonl"),
                )
            )
        if not stages:
            raise ValueError(
                f"No @a64forge_stage functions found in {path}. "
                "Use the YAML adapter or decorate stage functions."
            )
        return WorkflowSpec(name=path.stem, stages=stages)


def analyze_workflow(path: Path) -> WorkflowSpec:
    target = path.resolve()
    if target.is_dir():
        for name in ("workflow.yaml", "workflow.yml", "agent.py"):
            candidate = target / name
            if candidate.exists():
                target = candidate
                break
    for adapter in (YamlWorkflowAdapter(), PythonAgentAdapter()):
        if adapter.can_handle(target):
            return adapter.analyze(target)
    raise ValueError(f"No workflow adapter can analyze {target}")
