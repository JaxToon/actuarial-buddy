"""Persist a run: snapshots → artifact store, outputs → data/outputs/<run_id>/, manifest → SQLite.

Stored per run (manifest schema 2):
- raw uploaded file bytes (when the data came from an upload) and the mapped canonical input
  table, as content-addressed artifacts;
- cleaned exposure/claims tables and the full row-level validation issue list (every
  excluded row with its reason codes);
- column mapping, validation config, study config, assumption snapshot, current-rate basis;
- code version (package, method, git SHA), Python/platform and dependency fingerprint;
- SHA-256 of every output file. ``manifest.json`` is the exact byte string whose hash is
  stored in SQLite.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from actuarybench.ingestion.validation import ValidationConfig, ValidationResult
from actuarybench.persistence.artifacts import ArtifactStore
from actuarybench.persistence.repositories import RunRepository
from actuarybench.pricing.scenario import PricingRun
from actuarybench.reporting.manifest import build_run_manifest, canonical_json, csv_bytes
from actuarybench.reporting.report import render_html_report, results_workbook_sheets
from actuarybench.reporting.workbook import to_xlsx_bytes
from actuarybench.utils.hashing import sha256_bytes

OUTPUT_FILES = ["report.html", "results.xlsx", "pricing_results.csv", "manifest.json"]


def save_run(
    run: PricingRun,
    source_files: dict[str, dict],
    exposures: ValidationResult,
    claims: ValidationResult,
    outputs_dir: Path,
    db_path: Path,
    synthetic: bool,
    mapped: dict[str, pd.DataFrame] | None = None,
    raw_files: dict[str, tuple[str, bytes] | None] | None = None,
    artifacts_dir: Path | None = None,
    validation_config: ValidationConfig | None = None,
) -> dict:
    """Write snapshots, report/workbook/CSV/manifest files and the immutable manifest record.

    ``mapped`` holds the canonical-named input tables exactly as validated; ``raw_files``
    optionally maps kind → (suffix, original uploaded bytes). ``artifacts_dir`` defaults to
    ``<outputs_dir>/../artifacts``.
    """
    store = ArtifactStore(artifacts_dir or Path(outputs_dir).parent / "artifacts")
    inputs = {k: dict(v) for k, v in source_files.items()}
    for kind in ("exposures", "claims"):
        info = inputs.setdefault(kind, {})
        raw = (raw_files or {}).get(kind)
        info["raw_artifact"] = store.put(raw[1], raw[0]) if raw else None
        df = (mapped or {}).get(kind)
        info["mapped_artifact"] = store.put(csv_bytes(df), ".csv") if df is not None else None
    issues = pd.concat([exposures.issues, claims.issues], ignore_index=True)
    artifacts = {
        "clean_exposures": store.put(csv_bytes(exposures.clean), ".csv"),
        "clean_claims": store.put(csv_bytes(claims.clean), ".csv"),
        "validation_issues": store.put(csv_bytes(issues), ".csv"),
    }

    manifest = build_run_manifest(
        run, inputs, exposures, claims, OUTPUT_FILES, artifacts, validation_config
    )
    out = Path(outputs_dir) / manifest["run_id"]
    out.mkdir(parents=True, exist_ok=False)
    (out / "report.html").write_text(render_html_report(run, manifest, synthetic), encoding="utf-8")
    (out / "results.xlsx").write_bytes(to_xlsx_bytes(results_workbook_sheets(run, manifest)))
    run.results.to_csv(out / "pricing_results.csv", index=False)
    manifest["output_hashes"] = {
        name: sha256_bytes((out / name).read_bytes())
        for name in OUTPUT_FILES
        if name != "manifest.json"
    }
    body = canonical_json(manifest)
    (out / "manifest.json").write_bytes(body)
    digest = RunRepository(db_path).save(manifest)
    if digest != sha256_bytes(body):  # both must be the same serialisation
        raise RuntimeError("Manifest serialisation mismatch between disk and database.")
    return {**manifest, "manifest_sha256": digest, "output_dir": str(out)}
