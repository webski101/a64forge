from __future__ import annotations

import json
import shutil
import tempfile
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel

from a64forge.schemas import BenchmarkRecord, HardwareInfo, OptimizationResult, RunLabel
from a64forge.storage import EvidenceStore


class EvidenceImport(BaseModel):
    run_id: str
    optimization_id: str
    records: int
    architecture: str
    status: str
    report: Path
    deployment: Path
    already_imported: bool = False


def _safe_extract(archive: Path, destination: Path) -> None:
    root = destination.resolve()
    with zipfile.ZipFile(archive) as bundle:
        for entry in bundle.infolist():
            target = (destination / entry.filename).resolve()
            if root != target and root not in target.parents:
                raise ValueError(f"Unsafe path in evidence archive: {entry.filename}")
        bundle.extractall(destination)


@contextmanager
def _artifact_root(source: Path) -> Iterator[Path]:
    source = source.resolve()
    if source.is_dir():
        yield source
        return
    if not source.is_file() or source.suffix.lower() != ".zip":
        raise ValueError("Evidence source must be a GitHub artifact ZIP or extracted directory")
    with tempfile.TemporaryDirectory(prefix="a64forge-evidence-") as temp:
        destination = Path(temp)
        _safe_extract(source, destination)
        yield destination


def import_evidence(
    source: Path,
    store: EvidenceStore,
    reports_dir: Path = Path("reports"),
    deployments_dir: Path = Path("dist"),
) -> EvidenceImport:
    """Validate and import a verified A64Forge artifact without relabelling data."""
    with _artifact_root(source) as root:
        report_manifests = sorted((root / "reports").glob("*/manifest.json"))
        result_files = sorted((root / "reports").glob("*/results.json"))
        record_files = sorted((root / "benchmarks").glob("*/*/*.json"))
        hardware_file = root / "evidence" / "system.json"
        deployment_manifest = root / "dist" / "a64forge-manifest.json"
        if len(report_manifests) != 1 or len(result_files) != 1 or not record_files:
            raise ValueError("Evidence archive is missing its report or benchmark records")
        if not hardware_file.is_file() or not deployment_manifest.is_file():
            raise ValueError("Evidence archive is missing host or deployment evidence")

        report_manifest = json.loads(report_manifests[0].read_text(encoding="utf-8"))
        deployment = json.loads(deployment_manifest.read_text(encoding="utf-8"))
        optimization = OptimizationResult.model_validate_json(
            result_files[0].read_text(encoding="utf-8")
        )
        hardware = HardwareInfo.model_validate_json(hardware_file.read_text(encoding="utf-8"))
        records = [
            BenchmarkRecord.model_validate_json(path.read_text(encoding="utf-8"))
            for path in record_files
        ]

        run_id = report_manifest.get("run_id")
        if not isinstance(run_id, str) or not run_id:
            raise ValueError("Evidence report has no run identifier")
        if optimization.run_id != run_id or any(record.run_id != run_id for record in records):
            raise ValueError("Evidence files do not share one benchmark run identifier")
        if report_manifest.get("run_label") != RunLabel.VERIFIED_ARM64.value:
            raise ValueError("Only a VERIFIED ARM64 RUN artifact can be imported")
        if not hardware.verified_arm64 or hardware.architecture not in {"arm64", "aarch64"}:
            raise ValueError("Host evidence does not describe a verified Arm64 run")
        if any(not record.verified_arm64 for record in records):
            raise ValueError("One or more benchmark records are not verified Arm64 measurements")
        if deployment.get("deployable") is not True or not optimization.deployable:
            raise ValueError("Evidence did not produce a deployable optimization")
        if deployment.get("benchmark_run_id") != run_id:
            raise ValueError("Deployment manifest references a different benchmark run")

        report_target = reports_dir.resolve() / run_id
        deployment_target = deployments_dir.resolve() / run_id
        report_target.mkdir(parents=True, exist_ok=True)
        deployment_target.mkdir(parents=True, exist_ok=True)
        for path in report_manifests[0].parent.iterdir():
            if path.is_file():
                shutil.copy2(path, report_target / path.name)
        for path in (root / "dist").iterdir():
            if path.is_file():
                shutil.copy2(path, deployment_target / path.name)

        already_imported = store.has_run(run_id)
        if not already_imported:
            store.save_records(records)
        store.save_optimization(optimization)
        created_at = str(report_manifest.get("generated_at") or datetime.now(UTC).isoformat())
        store.save_hardware(run_id, hardware, created_at)

        return EvidenceImport(
            run_id=run_id,
            optimization_id=optimization.optimization_id,
            records=len(records),
            architecture=hardware.architecture,
            status=optimization.status.value,
            report=report_target / "report.html",
            deployment=deployment_target,
            already_imported=already_imported,
        )
