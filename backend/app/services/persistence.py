from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class SQLiteRepository:
    """Small thread-safe metadata gateway; artifacts remain on the filesystem."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    progress REAL NOT NULL DEFAULT 0,
                    request_json TEXT NOT NULL,
                    result_json TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS artifacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
                    kind TEXT NOT NULL,
                    path TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_artifacts_job_id ON artifacts(job_id);
                """
            )

    def create_job(self, job_id: str, request: dict[str, Any]) -> dict[str, Any]:
        now = self._now()
        with self._lock, self._connect() as connection:
            connection.execute(
                "INSERT INTO jobs(id,status,progress,request_json,created_at,updated_at) VALUES(?,?,?,?,?,?)",
                (job_id, "queued", 0.0, json.dumps(request), now, now),
            )
        return self.get_job(job_id) or {}

    def update_job(
        self,
        job_id: str,
        *,
        status: str | None = None,
        progress: float | None = None,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> dict[str, Any]:
        assignments = ["updated_at = ?"]
        values: list[Any] = [self._now()]
        if status is not None:
            assignments.append("status = ?")
            values.append(status)
        if progress is not None:
            assignments.append("progress = ?")
            values.append(progress)
        if result is not None:
            assignments.append("result_json = ?")
            values.append(json.dumps(result))
        if error is not None:
            assignments.append("error = ?")
            values.append(error)
        values.append(job_id)
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                f"UPDATE jobs SET {', '.join(assignments)} WHERE id = ?", values
            )
            if cursor.rowcount == 0:
                raise KeyError(f"unknown job: {job_id}")
        return self.get_job(job_id) or {}

    def add_artifact(self, job_id: str, *, kind: str, path: str, size: int) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                "INSERT INTO artifacts(job_id,kind,path,size,created_at) VALUES(?,?,?,?,?)",
                (job_id, kind, path.replace("\\", "/"), size, self._now()),
            )

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self._lock, self._connect() as connection:
            row = connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
            if row is None:
                return None
            artifacts = connection.execute(
                "SELECT kind,path,size,created_at FROM artifacts WHERE job_id = ? ORDER BY id",
                (job_id,),
            ).fetchall()
        return self._job_dict(row, artifacts)

    def list_gallery(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM jobs WHERE status = 'completed' ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            result = []
            for row in rows:
                artifacts = connection.execute(
                    "SELECT kind,path,size,created_at FROM artifacts WHERE job_id = ? ORDER BY id",
                    (row["id"],),
                ).fetchall()
                result.append(self._job_dict(row, artifacts))
            return result

    @staticmethod
    def _job_dict(row: sqlite3.Row, artifacts: list[sqlite3.Row]) -> dict[str, Any]:
        request = json.loads(row["request_json"])
        result = json.loads(row["result_json"]) if row["result_json"] else {}
        artifact_values = [
            {
                "kind": item["kind"],
                "path": item["path"],
                "url": f"/artifacts/{item['path']}",
                "size": item["size"],
                "created_at": item["created_at"],
            }
            for item in artifacts
        ]
        return {
            "id": row["id"],
            "job_id": row["id"],
            "status": row["status"],
            "progress": row["progress"],
            "request": request,
            "error": row["error"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "artifacts": artifact_values,
            **result,
        }

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
