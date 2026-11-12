"""Repositories over the local SQLite database."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from actuarybench.persistence.database import connect
from actuarybench.schemas.assumptions import AssumptionSet
from actuarybench.utils.hashing import sha256_bytes


class DuplicateVersionError(ValueError):
    pass


class AssumptionRepository:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def _conn(self) -> sqlite3.Connection:
        return connect(self.db_path)

    def next_version(self, name: str) -> int:
        with self._conn() as c:
            (v,) = c.execute(
                "SELECT COALESCE(MAX(version), 0) FROM assumption_sets WHERE name = ?", (name,)
            ).fetchone()
        return int(v) + 1

    def save(self, a: AssumptionSet) -> None:
        try:
            with self._conn() as c:
                c.execute(
                    "INSERT INTO assumption_sets (name, version, created_at, payload) "
                    "VALUES (?, ?, ?, ?)",
                    (a.name, a.version, a.created_at.isoformat(), a.model_dump_json()),
                )
        except sqlite3.IntegrityError as exc:
            raise DuplicateVersionError(f"{a.label} already exists") from exc

    def list(self) -> list[AssumptionSet]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT payload FROM assumption_sets ORDER BY name, version"
            ).fetchall()
        return [AssumptionSet.model_validate_json(r[0]) for r in rows]

    def get(self, name: str, version: int) -> AssumptionSet | None:
        with self._conn() as c:
            row = c.execute(
                "SELECT payload FROM assumption_sets WHERE name = ? AND version = ?",
                (name, version),
            ).fetchone()
        return AssumptionSet.model_validate_json(row[0]) if row else None


class RunRepository:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def save(self, manifest: dict) -> str:
        body = json.dumps(manifest, sort_keys=True, default=str)
        digest = sha256_bytes(body.encode())
        with connect(self.db_path) as c:
            c.execute(
                "INSERT INTO runs (run_id, created_at, assumption_label, manifest, "
                "manifest_sha256) VALUES (?, ?, ?, ?, ?)",
                (
                    manifest["run_id"],
                    manifest["created_at"],
                    manifest.get("assumptions", {}).get("label"),
                    body,
                    digest,
                ),
            )
        return digest

    def list(self) -> list[dict]:
        with connect(self.db_path) as c:
            rows = c.execute(
                "SELECT manifest, manifest_sha256 FROM runs ORDER BY created_at DESC"
            ).fetchall()
        return [{**json.loads(m), "manifest_sha256": h} for m, h in rows]

    def get(self, run_id: str) -> dict | None:
        with connect(self.db_path) as c:
            row = c.execute(
                "SELECT manifest, manifest_sha256 FROM runs WHERE run_id = ?", (run_id,)
            ).fetchone()
        return {**json.loads(row[0]), "manifest_sha256": row[1]} if row else None
