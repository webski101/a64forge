from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from a64forge import __version__
from a64forge.api.events import broker
from a64forge.config import ConfigError, load_project_config, load_workflow
from a64forge.optimizer.compiler import compile_deployment
from a64forge.optimizer.service import optimize_records, override_baseline
from a64forge.profiler.hardware import detect_hardware
from a64forge.report.generator import generate_report
from a64forge.schemas import ProgressEvent
from a64forge.service import database_path, run_benchmarks
from a64forge.storage import EvidenceStore

app = FastAPI(title="A64Forge", version=__version__)


def _store() -> EvidenceStore:
    return EvidenceStore(database_path())


def _system_payload() -> dict[str, Any]:
    captured = _store().load_latest_hardware()
    if captured is not None:
        run_id, hardware = captured
        return {
            **hardware.model_dump(mode="json"),
            "evidence_source": "imported_verified_run",
            "evidence_run_id": run_id,
        }
    return {
        **detect_hardware().model_dump(mode="json"),
        "evidence_source": "current_host",
        "evidence_run_id": None,
    }


@app.get("/health")
def health() -> dict[str, object]:
    hardware = detect_hardware()
    return {
        "status": "ok",
        "version": __version__,
        "mode": "development" if hardware.dev_mode else "production",
        "verified_arm64": hardware.verified_arm64,
    }


@app.get("/system")
def system() -> dict[str, Any]:
    return _system_payload()


@app.get("/models")
def models() -> list[dict[str, Any]]:
    try:
        return [item.model_dump(mode="json") for item in load_project_config().models]
    except ConfigError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/workflows")
def workflows() -> list[dict[str, Any]]:
    try:
        config = load_project_config()
        return [load_workflow(config.workflow).model_dump(mode="json")]
    except ConfigError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/benchmarks")
def benchmarks(run_id: str | None = None) -> dict[str, Any]:
    store = _store()
    records = store.load_records(run_id)
    return {
        "runs": store.list_runs(),
        "records": [item.model_dump(mode="json") for item in records],
        "empty_message": None if records else "Not measured yet",
    }


@app.get("/optimizations")
def optimizations() -> dict[str, Any]:
    results = _store().load_optimizations()
    return {
        "items": [item.model_dump(mode="json") for item in results],
        "empty_message": None if results else "Not measured yet",
    }


async def _background_benchmark() -> None:
    try:
        config = load_project_config()
        await run_benchmarks(config, _store(), broker.publish)
    except Exception as exc:  # emitted to the UI; server remains healthy
        await broker.publish(ProgressEvent(event="error", message=str(exc)))


@app.post("/actions/benchmark", status_code=202)
async def start_benchmark(background: BackgroundTasks) -> dict[str, str]:
    background.add_task(_background_benchmark)
    return {"status": "started"}


@app.post("/actions/optimize")
def start_optimize(target: str = "balanced", run_id: str | None = None) -> dict[str, Any]:
    store = _store()
    records = store.load_records(run_id)
    if not records:
        raise HTTPException(status_code=409, detail="Not measured yet. Run a benchmark first.")
    previous = store.load_optimizations()
    if previous and previous[0].run_id == records[0].run_id:
        baseline_keys = {
            f"{item.model}:{item.quantization}:t{item.threads}:"
            f"b{item.batch_size}:c{item.context_size}"
            for item in previous[0].baseline
        }
        if len(baseline_keys) == 1:
            records = override_baseline(records, baseline_keys.pop())
    workflow = load_workflow(load_project_config().workflow)
    try:
        result = optimize_records(records, workflow, target)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    store.save_optimization(result)
    return result.model_dump(mode="json")


@app.post("/actions/compile")
def start_compile() -> dict[str, Any]:
    results = _store().load_optimizations()
    if not results:
        raise HTTPException(status_code=409, detail="Not measured yet. Optimize a benchmark first.")
    files = compile_deployment(results[0], Path("dist").resolve())
    return {
        "status": results[0].status.value,
        "deployable": results[0].deployable,
        "files": [str(item) for item in files],
    }


@app.post("/actions/report")
def start_report() -> dict[str, Any]:
    store = _store()
    results = store.load_optimizations()
    if not results:
        raise HTTPException(status_code=409, detail="Not measured yet. Optimize a benchmark first.")
    hardware = store.load_hardware(results[0].run_id) or detect_hardware()
    files = generate_report(results[0], hardware, Path("reports").resolve())
    return {"files": [str(item) for item in files]}


@app.get("/events")
async def events() -> StreamingResponse:
    queue = broker.subscribe()

    async def stream():
        try:
            yield "event: connected\ndata: {}\n\n"
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=20)
                    yield f"event: {event.event}\ndata: {event.model_dump_json()}\n\n"
                except TimeoutError:
                    yield "event: heartbeat\ndata: {}\n\n"
        finally:
            broker.unsubscribe(queue)

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.post("/v1/chat/completions")
async def chat_completions(payload: dict[str, Any]) -> JSONResponse:
    upstream = os.getenv("A64FORGE_UPSTREAM_URL")
    if not upstream:
        raise HTTPException(
            status_code=503,
            detail="No local llama-server is configured. Set A64FORGE_UPSTREAM_URL.",
        )
    async with httpx.AsyncClient(base_url=upstream, timeout=180) as client:
        response = await client.post("/v1/chat/completions", json=payload)
    return JSONResponse(status_code=response.status_code, content=response.json())


@app.post("/v1/workflows/{workflow_name}/run")
async def run_workflow(workflow_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    configured = load_workflow(load_project_config().workflow)
    if workflow_name != configured.name:
        raise HTTPException(status_code=404, detail=f"Unknown workflow {workflow_name}")
    results = _store().load_optimizations()
    if not results:
        raise HTTPException(status_code=409, detail="No compiled routing exists yet.")
    if not results[0].deployable:
        raise HTTPException(
            status_code=409,
            detail="No routing was compiled because at least one stage failed its quality gate.",
        )
    return {
        "workflow": workflow_name,
        "status": "routing_ready",
        "input": payload,
        "routing": {
            item.stage_id: item.selected.model for item in results[0].selections
        },
        "note": "Set A64FORGE_UPSTREAM_URL or run the generated multi-model deployment to execute inference.",
    }


frontend_dir = Path(os.getenv("A64FORGE_FRONTEND_DIR", "frontend/dist")).resolve()
if frontend_dir.exists():
    assets = frontend_dir / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str) -> FileResponse:
        candidate = frontend_dir / path
        return FileResponse(candidate if candidate.is_file() else frontend_dir / "index.html")
