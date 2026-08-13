from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Annotated

import typer

from a64forge.benchmark.runner import load_demo_records
from a64forge.config import ConfigError, load_project_config, load_workflow, write_default_project
from a64forge.evidence import import_evidence
from a64forge.optimizer.compiler import compile_deployment
from a64forge.optimizer.service import optimize_records, override_baseline
from a64forge.profiler.hardware import detect_hardware
from a64forge.profiler.workflow import analyze_workflow
from a64forge.report.generator import generate_report
from a64forge.schemas import ProgressEvent
from a64forge.service import autopilot as autopilot_service
from a64forge.service import database_path, run_benchmarks
from a64forge.storage import EvidenceStore

app = typer.Typer(no_args_is_help=True, help="Compile AI agent workflows for measured Arm64 efficiency.")


def _store() -> EvidenceStore:
    return EvidenceStore(database_path())


def _event(event: ProgressEvent) -> None:
    prefix = f"[{event.stage_id}] " if event.stage_id else ""
    typer.echo(f"{prefix}{event.message}")


@app.command()
def doctor(json_output: Annotated[bool, typer.Option("--json")] = False) -> None:
    """Inspect the real host, Arm features, runtimes, memory, and disk."""
    info = detect_hardware()
    if json_output:
        typer.echo(info.model_dump_json(indent=2))
        return
    typer.echo(f"A64Forge doctor — {'ARM64 verified' if info.verified_arm64 else 'development/unverified'}")
    for key, value in info.model_dump().items():
        typer.echo(f"{key:22} {value}")
    if not info.arm64:
        typer.echo("\nWARNING:\nThis machine is not Arm64. Development mode is supported, but official A64Forge performance measurements must run on an Arm64 machine.")


@app.command("init")
def initialize(destination: Path = Path("a64forge.yaml")) -> None:
    """Create a project configuration without overwriting existing work."""
    try:
        write_default_project(destination)
    except ConfigError as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(f"Created {destination}")


@app.command()
def analyze(path: Path) -> None:
    """Analyze a YAML workflow or decorated sample Python agent."""
    try:
        result = analyze_workflow(path)
    except (ConfigError, ValueError) as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(result.model_dump_json(indent=2))


@app.command("import-evidence")
def import_evidence_command(source: Path) -> None:
    """Import a verified Arm64 GitHub artifact into the local dashboard."""
    try:
        result = import_evidence(source, _store())
    except (OSError, ValueError) as exc:
        raise typer.BadParameter(str(exc)) from exc
    state = "Already imported" if result.already_imported else "Imported"
    typer.echo(
        f"{state} {result.records} VERIFIED ARM64 records — run {result.run_id}\n"
        f"Optimization: {result.status}\n"
        f"Report: {result.report}\n"
        f"Deployment: {result.deployment}"
    )


@app.command()
def benchmark(
    config_path: Annotated[Path | None, typer.Option("--config")] = None,
    demo_data: Annotated[Path | None, typer.Option("--demo-data", help="Explicit DEMO DATA fixture; never verified.")] = None,
    max_memory: Annotated[float | None, typer.Option("--max-memory")] = None,
    max_runtime: Annotated[int | None, typer.Option("--max-runtime")] = None,
    max_candidates: Annotated[int | None, typer.Option("--max-candidates")] = None,
) -> None:
    """Run a bounded real matrix, or explicitly import labelled demo fixtures."""
    store = _store()
    if demo_data:
        records = load_demo_records(demo_data)
        store.save_records(records)
        typer.echo(f"Imported {len(records)} records as DEMO DATA — run {records[0].run_id}")
        return
    config = load_project_config(config_path)
    if max_memory is not None:
        config.search.max_memory_gb = max_memory
    if max_runtime is not None:
        config.search.max_runtime_seconds = max_runtime
    if max_candidates is not None:
        config.search.max_candidates = max_candidates
    records = asyncio.run(run_benchmarks(config, store, _event))
    typer.echo(f"Stored {len(records)} measured records — run {records[0].run_id}")


@app.command()
def optimize(
    target: Annotated[str, typer.Option(help="latency, memory, throughput, balanced, or quality")] = "balanced",
    run_id: Annotated[str | None, typer.Option("--run-id")] = None,
    baseline: Annotated[
        str | None,
        typer.Option(
            "--baseline",
            help="Measured candidate key, for example large:Q4_K_M:t1:b64:c512.",
        ),
    ] = None,
) -> None:
    """Apply quality gates, compute Pareto frontiers, and select stage routing."""
    store = _store()
    records = store.load_records(run_id)
    if not records:
        raise typer.BadParameter("Not measured yet. Run `a64forge benchmark` first.")
    if baseline:
        try:
            records = override_baseline(records, baseline)
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from exc
    workflow = load_workflow(load_project_config().workflow)
    result = optimize_records(records, workflow, target)
    store.save_optimization(result)
    typer.echo(result.model_dump_json(indent=2))


@app.command("compile")
def compile_command(destination: Path = Path("dist")) -> None:
    """Compile the latest optimization into reusable deployment artifacts."""
    results = _store().load_optimizations()
    if not results:
        raise typer.BadParameter("Not measured yet. Run `a64forge optimize` first.")
    files = compile_deployment(results[0], destination.resolve())
    typer.echo("\n".join(str(item) for item in files))


@app.command()
def report(destination: Path = Path("reports")) -> None:
    """Generate a portable HTML/JSON evidence report."""
    results = _store().load_optimizations()
    if not results:
        raise typer.BadParameter("Not measured yet. Run `a64forge optimize` first.")
    hardware = _store().load_hardware(results[0].run_id) or detect_hardware()
    files = generate_report(results[0], hardware, destination.resolve())
    typer.echo("\n".join(str(item) for item in files))


@app.command()
def autopilot(config_path: Annotated[Path | None, typer.Option("--config")] = None) -> None:
    """Inspect, benchmark, optimize, compile, and report with safety limits."""
    result = asyncio.run(autopilot_service(config_path, _event))
    typer.echo(json.dumps(result, default=str, indent=2))


@app.command()
def serve(
    host: str = "127.0.0.1",
    port: int = 8640,
    reload: bool = False,
) -> None:
    """Serve the API and built dashboard."""
    try:
        import uvicorn
    except ImportError as exc:
        raise typer.BadParameter("Install the project first: pip install -e .") from exc
    uvicorn.run("a64forge.api.main:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    app()
