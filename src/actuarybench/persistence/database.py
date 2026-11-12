"""Local SQLite storage for assumption sets and run manifests (single-user prototype)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS assumption_sets (
    name TEXT NOT NULL,
    version INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    payload TEXT NOT NULL,
    PRIMARY KEY (name, version)
);
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    assumption_label TEXT,
    manifest TEXT NOT NULL,
    manifest_sha256 TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS assumption_sets_immutable
BEFORE UPDATE ON assumption_sets
BEGIN SELECT RAISE(ABORT, 'assumption sets are immutable; save a new version'); END;
CREATE TRIGGER IF NOT EXISTS runs_immutable
BEFORE UPDATE ON runs
BEGIN SELECT RAISE(ABORT, 'runs are immutable'); END;
"""


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    return conn
