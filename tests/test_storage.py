from pathlib import Path

from a64forge.storage import EvidenceStore


def test_sqlite_round_trip(tmp_path: Path, make_record) -> None:
    store = EvidenceStore(tmp_path / "evidence.db")
    record = make_record()
    store.save_records([record])
    loaded = store.load_records("demo-test")
    assert loaded == [record]
    assert store.list_runs()[0]["experiments"] == 1

