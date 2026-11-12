"""Persist a run: write outputs to data/outputs/<run_id>/ and the manifest to SQLite."""

from __future__ import annotations

import json
from pathlib import Path

from actuarybench.ingestion.validation import ValidationResult
from actuarybench.persistence.repositories import RunRepository
from actuarybench.pricing.scenario import PricingRun
from actuarybench.reporting.manifest import build_run_manifest
from actuarybench.reporting.report import render_html_report, results_workbook_sheets
from actuarybench.reporting.workbook import to_xlsx_bytes

OUTPUT_FILES = ["report.html", "results.xlsx", "pricing_results.csv", "manifest.json"]


def save_run(
    run: PricingRun,
    source_files: dict[str, dict],
    exposures: ValidationResult,
    claims: ValidationResult,
    outputs_dir: Path,
    db_path: Path,
    synthetic: bool,
) -> dict:
    """Write report/workbook/CSV/manifest files and store the immutable manifest."""
    manifest = build_run_manifest(run, source_files, exposures, claims, OUTPUT_FILES)
    out = outputs_dir / manifest["run_id"]
    out.mkdir(parents=True, exist_ok=False)
    (out / "report.html").write_text(render_html_report(run, manifest, synthetic), encoding="utf-8")
    (out / "results.xlsx").write_bytes(to_xlsx_bytes(results_workbook_sheets(run, manifest)))
    run.results.to_csv(out / "pricing_results.csv", index=False)
    (out / "manifest.json").write_text(
        json.dumps(manifest, indent=2, default=str), encoding="utf-8"
    )
    manifest["manifest_sha256"] = RunRepository(db_path).save(manifest)
    manifest["output_dir"] = str(out)
    return manifest
