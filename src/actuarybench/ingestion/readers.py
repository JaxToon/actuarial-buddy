"""Read uploaded CSV/XLSX files into raw (all-string) dataframes."""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import PurePath

import pandas as pd

from actuarybench.config import ALLOWED_UPLOAD_SUFFIXES, MAX_UPLOAD_BYTES
from actuarybench.utils.hashing import sha256_bytes


class UploadError(ValueError):
    """Raised for unsupported, oversized or unreadable uploads."""


@dataclass(frozen=True)
class RawTable:
    filename: str
    sha256: str
    sheet: str | None
    data: pd.DataFrame


def list_sheets(filename: str, content: bytes) -> list[str]:
    """Sheet names of an XLSX upload (empty list for CSV)."""
    _check(filename, content)
    if PurePath(filename).suffix.lower() == ".csv":
        return []
    try:
        return list(pd.ExcelFile(io.BytesIO(content), engine="openpyxl").sheet_names)
    except Exception as exc:  # noqa: BLE001 - surface any parser failure to the user
        raise UploadError(f"Could not open '{filename}' as XLSX: {exc}") from exc


def read_table(filename: str, content: bytes, sheet: str | None = None) -> RawTable:
    """Read a CSV or XLSX file. All cells are read as strings so that no value is silently
    coerced; typing happens later in validation where failures are reported per row."""
    _check(filename, content)
    suffix = PurePath(filename).suffix.lower()
    try:
        if suffix == ".csv":
            df = pd.read_csv(io.BytesIO(content), dtype=str, keep_default_na=False)
        else:
            df = pd.read_excel(
                io.BytesIO(content), sheet_name=sheet or 0, dtype=str, engine="openpyxl"
            )
            df = df.fillna("")
    except Exception as exc:  # noqa: BLE001
        raise UploadError(f"Could not read '{filename}': {exc}") from exc
    df.columns = [str(c).strip() for c in df.columns]
    df = df.apply(lambda s: s.str.strip())
    df = df.replace("", pd.NA)
    if df.empty:
        raise UploadError(f"'{filename}' contains no data rows.")
    return RawTable(filename=filename, sha256=sha256_bytes(content), sheet=sheet, data=df)


def _check(filename: str, content: bytes) -> None:
    suffix = PurePath(filename).suffix.lower()
    if suffix not in ALLOWED_UPLOAD_SUFFIXES:
        raise UploadError(
            f"Unsupported file type '{suffix or '(none)'}'. Allowed: "
            + ", ".join(ALLOWED_UPLOAD_SUFFIXES)
        )
    if len(content) > MAX_UPLOAD_BYTES:
        raise UploadError(
            f"'{filename}' is {len(content) / 1e6:.1f} MB; the limit is "
            f"{MAX_UPLOAD_BYTES / 1e6:.0f} MB."
        )
    if not content:
        raise UploadError(f"'{filename}' is empty.")
