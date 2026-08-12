from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel


class Route(BaseModel):
    model: str
    model_repo: str
    quantization: str
    threads: int
    batch_size: int
    context_size: int


class StageRouter:
    def __init__(self, routes: dict[str, Route]) -> None:
        self.routes = routes

    @classmethod
    def from_file(cls, path: Path) -> StageRouter:
        data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
        return cls({stage: Route.model_validate(value) for stage, value in data["routing"].items()})

    def for_stage(self, stage_id: str) -> Route:
        try:
            return self.routes[stage_id]
        except KeyError as exc:
            raise KeyError(f"No compiled route for stage {stage_id}") from exc

