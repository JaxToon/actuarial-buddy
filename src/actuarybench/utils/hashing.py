"""Hashing helpers for dataset fingerprints."""

from __future__ import annotations

import hashlib

import pandas as pd


def sha256_bytes(data: bytes) -> str:
    """Return the SHA-256 hex digest of raw bytes."""
    return hashlib.sha256(data).hexdigest()


def dataframe_fingerprint(df: pd.DataFrame) -> str:
    """Deterministic SHA-256 of a dataframe's CSV serialisation (columns + values, no index)."""
    return sha256_bytes(df.to_csv(index=False, lineterminator="\n").encode("utf-8"))
