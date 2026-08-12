from __future__ import annotations

import asyncio
import hashlib
import json
import os
import shutil
import socket
import subprocess
import time
import uuid
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import httpx
import psutil

from a64forge.benchmark.metrics import aggregate_latency, mean
from a64forge.benchmark.quality import score_output
from a64forge.schemas import (
    BenchmarkCandidate,
    BenchmarkRecord,
    HardwareInfo,
    ProgressEvent,
    RunLabel,
    SearchConfig,
    WorkflowStage,
)

ProgressCallback = Callable[[ProgressEvent], Awaitable[None] | None]


class BenchmarkError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dataset_hash(path: Path) -> str:
    return sha256_file(path)


def git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        ).stdout.strip() or "unknown"
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"


def load_dataset(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise BenchmarkError(f"Dataset not found: {path}")
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise BenchmarkError(f"Invalid JSONL at {path}:{line_number}: {exc}") from exc
        if "input" not in item or "expected" not in item:
            raise BenchmarkError(f"Dataset row {path}:{line_number} needs input and expected")
        rows.append(item)
    if not rows:
        raise BenchmarkError(f"Dataset is empty: {path}")
    return rows


class ResourceSampler:
    def __init__(self, pid: int) -> None:
        self.process = psutil.Process(pid)
        self.peak_rss = 0
        self.cpu: list[float] = []
        self.running = True

    async def sample(self) -> None:
        self.process.cpu_percent(None)
        while self.running:
            try:
                processes = [self.process, *self.process.children(recursive=True)]
                rss = sum(item.memory_info().rss for item in processes if item.is_running())
                cpu = sum(item.cpu_percent(None) for item in processes if item.is_running())
                self.peak_rss = max(self.peak_rss, rss)
                self.cpu.append(cpu)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            await asyncio.sleep(0.05)


class LlamaServerRunner:
    def __init__(
        self,
        hardware: HardwareInfo,
        search: SearchConfig,
        artifacts_dir: Path,
        executable: str | None = None,
    ) -> None:
        self.hardware = hardware
        self.search = search
        self.artifacts_dir = artifacts_dir
        self.executable: str = (
            executable or os.getenv("A64FORGE_LLAMA_SERVER") or "llama-server"
        )

    async def _emit(self, callback: ProgressCallback | None, event: ProgressEvent) -> None:
        if callback:
            result = callback(event)
            if asyncio.iscoroutine(result):
                await result

    @staticmethod
    def _port() -> int:
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            return int(sock.getsockname()[1])

    def _validate_candidate(self, candidate: BenchmarkCandidate) -> Path:
        if candidate.model_path is None:
            raise BenchmarkError(
                f"No local file configured for {candidate.model_id}/{candidate.quantization}. "
                "Download the model and set variants[].path in configs/default.yaml."
            )
        path = candidate.model_path.resolve()
        if not path.exists() or not path.is_file():
            raise BenchmarkError(f"Model file not found: {path}")
        available_limit = self.search.max_memory_gb or self.hardware.available_memory_gb * 0.8
        estimated_gb = path.stat().st_size * 1.25 / (1024**3) + candidate.context_size * 0.00015
        if estimated_gb > available_limit:
            raise BenchmarkError(
                f"Candidate requires an estimated {estimated_gb:.2f} GB, above the "
                f"{available_limit:.2f} GB safety limit. Adjust --max-memory or the matrix."
            )
        return path

    def _command(self, path: Path, candidate: BenchmarkCandidate, port: int) -> list[str]:
        executable = shutil.which(self.executable) or (
            str(Path(self.executable).resolve()) if Path(self.executable).exists() else None
        )
        if not executable:
            raise BenchmarkError(
                "A64Forge could not find llama-server. Run scripts/build_llama_cpp.sh "
                "or configure A64FORGE_LLAMA_SERVER."
            )
        command = [executable]
        if Path(executable).name in {"llama", "llama.exe"}:
            command.append("serve")
        return [
            *command,
            "-m",
            str(path),
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--threads",
            str(candidate.threads),
            "--threads-batch",
            str(candidate.threads),
            "--batch-size",
            str(candidate.batch_size),
            "--ctx-size",
            str(candidate.context_size),
            "--metrics",
        ]

    async def _wait_ready(self, client: httpx.AsyncClient, process: asyncio.subprocess.Process) -> None:
        deadline = time.monotonic() + min(120, self.search.request_timeout_seconds)
        while time.monotonic() < deadline:
            if process.returncode is not None:
                raise BenchmarkError(
                    "llama-server exited during startup; inspect the candidate server log"
                )
            try:
                response = await client.get("/health", timeout=2)
                if response.status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            await asyncio.sleep(0.25)
        raise BenchmarkError("llama-server did not become healthy before the startup timeout")

    async def _request(
        self, client: httpx.AsyncClient, stage: WorkflowStage, item: dict[str, Any]
    ) -> dict[str, Any]:
        payload = {
            "model": "a64forge-local",
            "messages": [
                {"role": "system", "content": f"{stage.prompt}\nReturn only the requested answer."},
                {"role": "user", "content": str(item["input"]) + "\n/no_think"},
            ],
            "temperature": stage.temperature,
            "max_tokens": stage.max_tokens,
            "stream": False,
            "cache_prompt": False,
        }
        start = time.perf_counter()
        response = await client.post(
            "/v1/chat/completions", json=payload, timeout=self.search.request_timeout_seconds
        )
        latency_ms = (time.perf_counter() - start) * 1000
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        timings = data.get("timings", {})
        usage = data.get("usage", {})
        return {
            "content": content,
            "latency_ms": latency_ms,
            "prompt_tokens": usage.get("prompt_tokens", timings.get("prompt_n")),
            "generated_tokens": usage.get("completion_tokens", timings.get("predicted_n")),
            "prompt_tps": timings.get("prompt_per_second"),
            "generation_tps": timings.get("predicted_per_second"),
            "ttft_ms": data.get("timings", {}).get("ttft_ms"),
            "raw": data,
        }

    async def run(
        self,
        run_id: str,
        stage: WorkflowStage,
        candidate: BenchmarkCandidate,
        callback: ProgressCallback | None = None,
    ) -> BenchmarkRecord:
        model_path = self._validate_candidate(candidate)
        rows = load_dataset(stage.dataset)
        port = self._port()
        command = self._command(model_path, candidate, port)
        artifact_path = (
            self.artifacts_dir
            / run_id
            / stage.id
            / f"{candidate.key.replace(':', '_')}.json"
        )
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        server_log_path = artifact_path.with_suffix(".server.log")
        await self._emit(
            callback,
            ProgressEvent(
                event="candidate_start",
                message=f"Loading {candidate.model_name} / {candidate.quantization}",
                stage_id=stage.id,
                candidate_key=candidate.key,
            ),
        )
        started = time.perf_counter()
        server_log = server_log_path.open("wb")
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=server_log,
                stderr=asyncio.subprocess.STDOUT,
            )
        except BaseException:
            server_log.close()
            raise
        sampler = ResourceSampler(process.pid)
        sampler_task = asyncio.create_task(sampler.sample())
        responses: list[dict[str, Any]] = []
        error: str | None = None
        try:
            async with httpx.AsyncClient(base_url=f"http://127.0.0.1:{port}") as client:
                await self._wait_ready(client, process)
                load_ms = (time.perf_counter() - started) * 1000
                for _ in range(self.search.warmups):
                    await self._request(client, stage, rows[0])
                for repetition in range(self.search.repetitions):
                    for item in rows:
                        await self._emit(
                            callback,
                            ProgressEvent(
                                event="measure",
                                message=f"Measuring pass {repetition + 1}/{self.search.repetitions}",
                                stage_id=stage.id,
                                candidate_key=candidate.key,
                            ),
                        )
                        response = await self._request(client, stage, item)
                        response["quality"] = score_output(
                            stage.quality_metric, response["content"], item["expected"]
                        )
                        responses.append(response)
        except (BenchmarkError, httpx.HTTPError, KeyError, ValueError) as exc:
            load_ms = (time.perf_counter() - started) * 1000
            error = str(exc)
        finally:
            sampler.running = False
            await sampler_task
            if process.returncode is None:
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=8)
                except TimeoutError:
                    process.kill()
                    await process.wait()
            server_log.close()
        server_log_tail = server_log_path.read_text(
            encoding="utf-8", errors="replace"
        )[-4000:]

        latencies = [float(item["latency_ms"]) for item in responses]
        median_latency, p95_latency = aggregate_latency(latencies)
        generated = [int(item["generated_tokens"]) for item in responses if item["generated_tokens"]]
        total_tokens = [
            int(item["prompt_tokens"] or 0) + int(item["generated_tokens"] or 0)
            for item in responses
        ]
        total_seconds = sum(latencies) / 1000 if latencies else 0
        record = BenchmarkRecord(
            run_id=run_id,
            git_commit=git_commit(),
            hostname=self.hardware.hostname,
            architecture=self.hardware.architecture,
            cpu=self.hardware.cpu_model,
            cores=self.hardware.logical_cores,
            ram_gb=self.hardware.memory_gb,
            stage_id=stage.id,
            model=candidate.model_id,
            model_repo=candidate.model_repo,
            model_hash=sha256_file(model_path),
            quantization=candidate.quantization,
            threads=candidate.threads,
            batch_size=candidate.batch_size,
            context_size=candidate.context_size,
            prompt_tokens=sum(int(item["prompt_tokens"] or 0) for item in responses),
            generated_tokens=sum(generated),
            latency_ms=mean(latencies),
            median_latency_ms=median_latency,
            p95_latency_ms=p95_latency,
            ttft_ms=mean([float(item["ttft_ms"]) for item in responses if item["ttft_ms"]]),
            prompt_tokens_per_second=mean(
                [float(item["prompt_tps"]) for item in responses if item["prompt_tps"]]
            ),
            generation_tokens_per_second=mean(
                [float(item["generation_tps"]) for item in responses if item["generation_tps"]]
            ),
            total_tokens_per_second=sum(total_tokens) / total_seconds if total_seconds else None,
            requests_per_minute=len(responses) / total_seconds * 60 if total_seconds else None,
            peak_memory_mb=sampler.peak_rss / (1024**2) if sampler.peak_rss else None,
            average_cpu_percent=mean(sampler.cpu),
            peak_cpu_percent=max(sampler.cpu) if sampler.cpu else None,
            model_size_bytes=model_path.stat().st_size,
            load_time_ms=load_ms,
            quality_score=mean([float(item["quality"]) for item in responses]),
            measured_runs=len(responses),
            warmup_runs=self.search.warmups,
            run_label=(
                RunLabel.VERIFIED_ARM64 if self.hardware.verified_arm64 else RunLabel.UNVERIFIED
            ),
            verified_arm64=self.hardware.verified_arm64,
            dataset_hash=dataset_hash(stage.dataset),
            error=error,
            raw_artifact=artifact_path,
            metadata={
                "command": command,
                "server_log": str(server_log_path),
                "server_log_tail": server_log_tail,
            },
        )
        artifact_path.write_text(record.model_dump_json(indent=2), encoding="utf-8")
        await self._emit(
            callback,
            ProgressEvent(
                event="candidate_end",
                message="Candidate measured" if not error else f"Candidate failed: {error}",
                stage_id=stage.id,
                candidate_key=candidate.key,
            ),
        )
        return record


def load_demo_records(path: Path, run_id: str | None = None) -> list[BenchmarkRecord]:
    """Load explicitly labelled deterministic fixtures for UI/tests only."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    selected_run_id = run_id or f"demo-{uuid.uuid4().hex[:8]}"
    records: list[BenchmarkRecord] = []
    for item in payload:
        item = dict(item)
        item["run_id"] = selected_run_id
        item["run_label"] = RunLabel.DEVELOPMENT
        item["verified_arm64"] = False
        records.append(BenchmarkRecord.model_validate(item))
    return records
