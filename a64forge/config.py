from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from a64forge.schemas import ProjectConfig, WorkflowSpec


class ConfigError(RuntimeError):
    pass


def env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def project_root() -> Path:
    return Path(os.getenv("A64FORGE_HOME", ".")).resolve()


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ConfigError(f"Configuration file not found: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"Expected a YAML mapping in {path}")
    return data


def load_project_config(path: Path | None = None) -> ProjectConfig:
    config_path = (path or Path(os.getenv("A64FORGE_CONFIG", "configs/default.yaml"))).resolve()
    try:
        config = ProjectConfig.model_validate(_load_yaml(config_path))
    except ValidationError as exc:
        raise ConfigError(f"Invalid A64Forge config {config_path}:\n{exc}") from exc
    base = config_path.parent.parent if config_path.parent.name == "configs" else config_path.parent
    config.workflow = (base / config.workflow).resolve() if not config.workflow.is_absolute() else config.workflow
    for model in config.models:
        for variant in model.variants:
            if variant.path and not variant.path.is_absolute():
                variant.path = (base / variant.path).resolve()
    return config


def load_workflow(path: Path) -> WorkflowSpec:
    try:
        workflow = WorkflowSpec.model_validate(_load_yaml(path))
    except ValidationError as exc:
        raise ConfigError(f"Invalid workflow {path}:\n{exc}") from exc
    for stage in workflow.stages:
        if not stage.dataset.is_absolute():
            stage.dataset = (path.parent / stage.dataset).resolve()
    return workflow


def write_default_project(destination: Path) -> None:
    source = Path(__file__).resolve().parent.parent / "configs" / "default.yaml"
    if destination.exists():
        raise ConfigError(f"Refusing to overwrite existing file: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

