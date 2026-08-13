from pathlib import Path

from a64forge.schemas import Detection, HardwareInfo
from a64forge.storage import EvidenceStore


def test_sqlite_round_trip(tmp_path: Path, make_record) -> None:
    store = EvidenceStore(tmp_path / "evidence.db")
    record = make_record()
    store.save_records([record])
    loaded = store.load_records("demo-test")
    assert loaded == [record]
    assert store.list_runs()[0]["experiments"] == 1


def test_hardware_snapshot_round_trip(tmp_path: Path) -> None:
    store = EvidenceStore(tmp_path / "evidence.db")
    hardware = HardwareInfo(
        architecture="aarch64", cpu_model="Arm fixture", logical_cores=4, physical_cores=4,
        memory_gb=16, available_memory_gb=8, os="Linux", hostname="fixture", arm64=True,
        neon=Detection.DETECTED, sve=Detection.UNKNOWN, sve2=Detection.UNKNOWN,
        arm_fma=Detection.UNKNOWN, matmul_int8=Detection.DETECTED, disk_free_gb=10,
        dev_mode=False,
    )
    store.save_hardware("run-1", hardware, "2026-01-01T00:00:00+00:00")
    assert store.load_latest_hardware() == ("run-1", hardware)
