"""XLSX/CSV serialisation helpers."""

from __future__ import annotations

import io

import pandas as pd

from actuarybench.ingestion.validation import ValidationResult, validation_summary


def to_xlsx_bytes(sheets: dict[str, pd.DataFrame]) -> bytes:
    """Write {sheet_name: dataframe} to an in-memory XLSX workbook."""
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as xw:
        for name, df in sheets.items():
            out = df.copy()
            for col in out.columns:
                if isinstance(out[col].dtype, pd.DatetimeTZDtype):
                    out[col] = out[col].dt.tz_localize(None)
            out.to_excel(xw, sheet_name=name[:31], index=False)
    return buf.getvalue()


def validation_report_sheets(
    results: list[ValidationResult], source_files: dict[str, dict] | None = None
) -> dict[str, pd.DataFrame]:
    """Sheets for a downloadable validation report."""
    sheets: dict[str, pd.DataFrame] = {"summary": validation_summary(results)}
    if source_files:
        sheets["source_files"] = pd.DataFrame(
            [{"record_type": k, **v} for k, v in source_files.items()]
        )
    for r in results:
        sheets[f"{r.record_type}_reconciliation"] = r.reconciliation()
        sheets[f"{r.record_type}_exclusions"] = r.excluded_by_reason()
        sheets[f"{r.record_type}_warnings"] = r.warnings_by_reason()
        sheets[f"{r.record_type}_issues"] = r.issues
        if r.derivations:
            sheets[f"{r.record_type}_derivations"] = pd.DataFrame({"derivation": r.derivations})
    return sheets
