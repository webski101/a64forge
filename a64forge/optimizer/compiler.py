from __future__ import annotations

import json
from pathlib import Path

import yaml

from a64forge.schemas import OptimizationResult


def compile_deployment(result: OptimizationResult, destination: Path) -> list[Path]:
    destination.mkdir(parents=True, exist_ok=True)
    routing = {
        "version": "1",
        "workflow": result.workflow,
        "run_id": result.run_id,
        "run_label": result.run_label.value,
        "routing": {
            selection.stage_id: {
                "model": selection.selected.model,
                "model_repo": selection.selected.model_repo,
                "quantization": selection.selected.quantization,
                "threads": selection.selected.threads,
                "batch_size": selection.selected.batch_size,
                "context_size": selection.selected.context_size,
                "quality_score": selection.selected.quality_score,
                "selection_score": selection.score,
            }
            for selection in result.selections
        },
    }
    manifest = {
        "version": "1",
        "architecture": "arm64" if result.run_label.value == "VERIFIED ARM64 RUN" else "unverified",
        "workflow": result.workflow,
        "benchmark_run_id": result.run_id,
        "optimization_id": result.optimization_id,
        "evidence_label": result.run_label.value,
        "stages": routing["routing"],
    }
    models = {
        "models": sorted(
            {
                (item.selected.model, item.selected.model_repo, item.selected.quantization)
                for item in result.selections
            }
        )
    }
    files = {
        "routing.yaml": yaml.safe_dump(routing, sort_keys=False),
        "models.yaml": yaml.safe_dump(
            {
                "models": [
                    {"id": model, "repo": repo, "quantization": quant}
                    for model, repo, quant in models["models"]
                ]
            },
            sort_keys=False,
        ),
        "a64forge-manifest.json": json.dumps(manifest, indent=2),
        "benchmark-summary.json": result.model_dump_json(indent=2),
        "Dockerfile.arm64": """FROM --platform=linux/arm64 python:3.12-slim\nWORKDIR /app\nCOPY . .\nRUN pip install a64forge\nCMD [\"a64forge\", \"serve\", \"--host\", \"0.0.0.0\"]\n""",
        "docker-compose.yml": """services:\n  a64forge:\n    build:\n      context: .\n      dockerfile: Dockerfile.arm64\n      platforms: [\"linux/arm64\"]\n    platform: linux/arm64\n    ports: [\"8640:8640\"]\n""",
        "README.md": (
            f"# Compiled {result.workflow} deployment\n\n"
            f"Evidence: **{result.run_label.value}**  \n"
            f"Benchmark run: `{result.run_id}`  \n"
            f"Optimization target: `{result.target}`\n\n"
            "Review `routing.yaml`, mount the listed GGUF files, then run "
            "`docker compose up --build`. Never present this deployment as Arm-verified "
            "unless the evidence label above is `VERIFIED ARM64 RUN`.\n"
        ),
    }
    output = []
    for name, content in files.items():
        path = destination / name
        path.write_text(content, encoding="utf-8")
        output.append(path)
    return output

