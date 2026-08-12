import json
from pathlib import Path

from a64forge.optimizer.compiler import compile_deployment
from a64forge.optimizer.service import optimize_records
from a64forge.report.generator import generate_report
from a64forge.schemas import Detection, HardwareInfo


def test_optimize_compile_report_pipeline(tmp_path: Path, make_record, sample_workflow) -> None:
    baseline = make_record(model="large", latency=150, memory=900, throughput=40, quality=0.96, baseline=True)
    winner = make_record(model="small", latency=70, memory=450, throughput=90, quality=0.95)
    result = optimize_records([baseline, winner], sample_workflow)
    compiled = compile_deployment(result, tmp_path / "dist")
    manifest = json.loads((tmp_path / "dist" / "a64forge-manifest.json").read_text())
    assert manifest["architecture"] == "unverified"
    assert manifest["stages"]["classify"]["model"] == "small"
    assert len(compiled) == 7
    hardware = HardwareInfo(
        architecture="x86_64", cpu_model="fixture", logical_cores=8, physical_cores=4,
        memory_gb=16, available_memory_gb=8, os="test", hostname="fixture", arm64=False,
        neon=Detection.UNKNOWN, sve=Detection.UNKNOWN, sve2=Detection.UNKNOWN,
        arm_fma=Detection.UNKNOWN, matmul_int8=Detection.UNKNOWN, disk_free_gb=10, dev_mode=True,
    )
    reports = generate_report(result, hardware, tmp_path / "reports")
    assert len(reports) == 3
    assert "DEMO DATA" in reports[0].read_text(encoding="utf-8")

