from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from pathlib import Path

from a64forge.schemas import BenchmarkRecord, HardwareInfo, OptimizationResult


class EvidenceStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS benchmark_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    stage_id TEXT NOT NULL,
                    candidate_key TEXT NOT NULL,
                    run_label TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_benchmark_run ON benchmark_records(run_id);
                CREATE TABLE IF NOT EXISTS optimizations (
                    optimization_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    target TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS hardware_snapshots (
                    run_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )

    def save_records(self, records: Iterable[BenchmarkRecord]) -> None:
        rows = []
        for record in records:
            candidate_key = (
                f"{record.model}:{record.quantization}:t{record.threads}:"
                f"b{record.batch_size}:c{record.context_size}"
            )
            rows.append(
                (
                    record.run_id,
                    record.stage_id,
                    candidate_key,
                    record.run_label.value,
                    record.model_dump_json(),
                    record.timestamp.isoformat(),
                )
            )
        with self._connect() as connection:
            connection.executemany(
                "INSERT INTO benchmark_records "
                "(run_id, stage_id, candidate_key, run_label, payload, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                rows,
            )

    def has_run(self, run_id: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM benchmark_records WHERE run_id = ? LIMIT 1", (run_id,)
            ).fetchone()
            return row is not None

    def load_records(self, run_id: str | None = None) -> list[BenchmarkRecord]:
        query = "SELECT payload FROM benchmark_records"
        params: tuple[str, ...] = ()
        if run_id:
            query += " WHERE run_id = ?"
            params = (run_id,)
        query += " ORDER BY id"
        with self._connect() as connection:
            return [
                BenchmarkRecord.model_validate_json(row["payload"])
                for row in connection.execute(query, params)
            ]

    def list_runs(self) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT run_id, MIN(created_at) timestamp, COUNT(*) experiments, "
                "MIN(run_label) run_label FROM benchmark_records GROUP BY run_id "
                "ORDER BY timestamp DESC"
            )
            return [dict(row) for row in rows]

    def save_optimization(self, result: OptimizationResult) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO optimizations "
                "(optimization_id, run_id, target, payload, created_at) VALUES (?, ?, ?, ?, ?)",
                (
                    result.optimization_id,
                    result.run_id,
                    result.target,
                    result.model_dump_json(),
                    result.timestamp.isoformat(),
                ),
            )

    def load_optimizations(self) -> list[OptimizationResult]:
        with self._connect() as connection:
            rows = connection.execute("SELECT payload FROM optimizations ORDER BY created_at DESC")
            return [OptimizationResult.model_validate(json.loads(row["payload"])) for row in rows]

    def save_hardware(self, run_id: str, hardware: HardwareInfo, created_at: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO hardware_snapshots "
                "(run_id, payload, created_at) VALUES (?, ?, ?)",
                (run_id, hardware.model_dump_json(), created_at),
            )

    def load_latest_hardware(self) -> tuple[str, HardwareInfo] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT run_id, payload FROM hardware_snapshots ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
        if row is None:
            return None
        return row["run_id"], HardwareInfo.model_validate_json(row["payload"])

    def load_hardware(self, run_id: str) -> HardwareInfo | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM hardware_snapshots WHERE run_id = ?", (run_id,)
            ).fetchone()
        return None if row is None else HardwareInfo.model_validate_json(row["payload"])
