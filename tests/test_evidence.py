import json
from pathlib import Path

from a64forge.evidence import import_evidence
from a64forge.optimizer.compiler import compile_deployment
from a64forge.optimizer.service import optimize_records
from a64forge.report.generator import generate_report
from a64forge.schemas import Detection, HardwareInfo, RunLabel
from a64forge.storage import EvidenceStore


def test_import_verified_evidence_is_validated_and_idempotent(
    tmp_path: Path, make_record, sample_workflow
) -> None:
    verified_fields = {
        "run_id": "verified-test",
        "architecture": "aarch64",
        "cpu": "Arm fixture",
        "run_label": RunLabel.VERIFIED_ARM64,
        "verified_arm64": True,
    }
    baseline = make_record(
        model="large", latency=150, memory=900, throughput=40, quality=0.96, baseline=True
    ).model_copy(update=verified_fields)
    winner = make_record(
        model="small", latency=70, memory=450, throughput=90, quality=0.95
    ).model_copy(update=verified_fields)
    optimization = optimize_records([baseline, winner], sample_workflow)
    artifact = tmp_path / "artifact"
    compile_deployment(optimization, artifact / "dist")
    hardware = HardwareInfo(
        architecture="aarch64", cpu_model="Arm fixture", logical_cores=4, physical_cores=4,
        memory_gb=16, available_memory_gb=8, os="Linux", hostname="fixture", arm64=True,
        neon=Detection.DETECTED, sve=Detection.DETECTED, sve2=Detection.DETECTED,
        arm_fma=Detection.UNKNOWN, matmul_int8=Detection.DETECTED, llama_server=True,
        llama_bench=True, disk_free_gb=10, dev_mode=False,
    )
    generate_report(optimization, hardware, artifact / "reports")
    benchmark_dir = artifact / "benchmarks" / "verified-test" / "classify"
    benchmark_dir.mkdir(parents=True)
    for index, record in enumerate([baseline, winner]):
        (benchmark_dir / f"record-{index}.json").write_text(
            record.model_dump_json(indent=2), encoding="utf-8"
        )
    evidence_dir = artifact / "evidence"
    evidence_dir.mkdir()
    (evidence_dir / "system.json").write_text(hardware.model_dump_json(indent=2), encoding="utf-8")

    store = EvidenceStore(tmp_path / "dashboard.db")
    imported = import_evidence(
        artifact, store, tmp_path / "imported-reports", tmp_path / "imported-dist"
    )
    assert imported.run_id == "verified-test"
    assert imported.records == 2
    assert imported.status == "DEPLOYABLE"
    assert imported.report.is_file()
    assert len(store.load_records("verified-test")) == 2
    captured = store.load_latest_hardware()
    assert captured is not None
    assert captured[0] == "verified-test"
    assert captured[1].verified_arm64 is True

    repeated = import_evidence(
        artifact, store, tmp_path / "imported-reports", tmp_path / "imported-dist"
    )
    assert repeated.already_imported is True
    assert len(store.load_records("verified-test")) == 2


def test_import_rejects_unverified_artifact(tmp_path: Path) -> None:
    artifact = tmp_path / "artifact"
    (artifact / "reports" / "run").mkdir(parents=True)
    (artifact / "benchmarks" / "run" / "stage").mkdir(parents=True)
    (artifact / "evidence").mkdir()
    (artifact / "dist").mkdir()
    (artifact / "reports" / "run" / "manifest.json").write_text(
        json.dumps({"run_id": "run", "run_label": "UNVERIFIED RUN"}), encoding="utf-8"
    )
    (artifact / "reports" / "run" / "results.json").write_text("{}", encoding="utf-8")
    (artifact / "benchmarks" / "run" / "stage" / "record.json").write_text(
        "{}", encoding="utf-8"
    )
    (artifact / "evidence" / "system.json").write_text("{}", encoding="utf-8")
    (artifact / "dist" / "a64forge-manifest.json").write_text("{}", encoding="utf-8")

    store = EvidenceStore(tmp_path / "dashboard.db")
    try:
        import_evidence(artifact, store)
    except ValueError:
        pass
    else:
        raise AssertionError("unverified evidence must not be imported")
