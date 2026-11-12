"""Run manifests, artifact integrity verification and recalculation (ACTUARIAL_METHODS §12).

Three separate claims are distinguished and never conflated:

1. **Artifact integrity** (:func:`verify_run_integrity`): the stored manifest, input/cleaned
   snapshots, exclusion details and output files still exist and match their SHA-256 hashes.
   Says nothing about whether the numbers can be recomputed.
2. **Recalculation** (:func:`recalculate_run`): re-runs validation → study → pricing from the
   stored input snapshot with the *currently installed* code and dependencies and compares
   result hashes. If the code or dependency fingerprint differs from the saved run, a match
   shows only that today's software reproduces the numbers — not that the historical
   environment was re-executed.
3. **Workspace comparison** (:func:`reproduce_run`): re-runs against the data currently
   loaded in the app.

Cross-version execution reproducibility is not claimed: the historical software environment
is recorded (git SHA, package versions) but not archived.
"""

from __future__ import annotations

import io
import json
import platform
import subprocess
import uuid
from dataclasses import asdict
from datetime import UTC, date, datetime
from importlib import metadata
from pathlib import Path

import pandas as pd

import actuarybench
from actuarybench.config import PROJECT_ROOT
from actuarybench.ingestion.validation import (
    ValidationConfig,
    ValidationResult,
    validate_claims_data,
    validate_exposure_data,
)
from actuarybench.persistence.artifacts import ArtifactStore
from actuarybench.pricing.scenario import PricingRun, run_pricing
from actuarybench.schemas.assumptions import AssumptionSet
from actuarybench.studies.segmentation import StudyConfig, run_experience_study
from actuarybench.utils.hashing import dataframe_fingerprint, sha256_bytes

MANIFEST_SCHEMA = 2
TRACKED_PACKAGES = ("streamlit", "pandas", "numpy", "pydantic", "plotly", "openpyxl", "xlsxwriter")


def canonical_json(obj: dict) -> bytes:
    """The exact serialisation that is hashed, stored in SQLite and written to disk."""
    return json.dumps(obj, sort_keys=True, default=str).encode("utf-8")


def code_version() -> dict:
    """Package/method version and git commit (``-dirty`` if tracked files are modified)."""
    out = {
        "package": actuarybench.__version__,
        "method": actuarybench.METHOD_VERSION,
        "git_commit": "unknown",
    }
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        ).stdout
        dirty = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()
        out["git_commit"] = commit.strip() + ("-dirty" if dirty else "")
    except (OSError, subprocess.SubprocessError):
        pass
    return out


def environment_info() -> dict:
    packages = {}
    for name in TRACKED_PACKAGES:
        try:
            packages[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            packages[name] = "not installed"
    env = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": packages,
    }
    env["dependency_fingerprint"] = sha256_bytes(
        canonical_json({"python": env["python"], "packages": packages})
    )
    return env


def study_config_to_dict(cfg: StudyConfig) -> dict:
    d = asdict(cfg)
    for k in ("period_start", "period_end", "evaluation_date"):
        d[k] = d[k].isoformat()
    d["segment_by"] = list(cfg.segment_by)
    return d


def study_config_from_dict(d: dict) -> StudyConfig:
    return StudyConfig(
        period_start=date.fromisoformat(d["period_start"]),
        period_end=date.fromisoformat(d["period_end"]),
        evaluation_date=date.fromisoformat(d["evaluation_date"]),
        claim_basis=d["claim_basis"],
        segment_by=tuple(d["segment_by"]),
        low_exposure_threshold_mm=float(d["low_exposure_threshold_mm"]),
    )


def _validation_block(r: ValidationResult) -> dict:
    return {
        "rows_in": r.rows_in,
        "rows_out": r.rows_out,
        "excluded_by_reason": r.excluded_by_reason()[["code", "rows"]].to_dict("records"),
        "warnings_by_reason": r.warnings_by_reason()[["code", "rows"]].to_dict("records"),
        "derivations": list(r.derivations),
    }


def results_fingerprint(run: PricingRun) -> dict[str, str]:
    s = run.study
    return {
        "pricing_results": dataframe_fingerprint(run.results),
        "experience_by_segment": dataframe_fingerprint(s.by_segment),
        "experience_by_period": dataframe_fingerprint(s.by_period),
    }


def csv_bytes(df: pd.DataFrame) -> bytes:
    """Serialisation used for data snapshots (identical to ``dataframe_fingerprint`` input)."""
    return df.to_csv(index=False, lineterminator="\n").encode("utf-8")


def _assumptions_from_manifest(manifest: dict) -> AssumptionSet:
    payload = {k: v for k, v in manifest["assumptions"].items() if k != "label"}
    payload["period_weights"] = {int(k): v for k, v in payload["period_weights"].items()}
    return AssumptionSet.model_validate(payload)


def build_run_manifest(
    run: PricingRun,
    source_files: dict[str, dict],
    exposures: ValidationResult,
    claims: ValidationResult,
    output_files: list[str] | None = None,
    artifacts: dict | None = None,
    validation_config: ValidationConfig | None = None,
) -> dict:
    a: AssumptionSet = run.assumptions
    overall = run.results[run.results["segment"] == "ALL"].iloc[0]
    return {
        "manifest_schema": MANIFEST_SCHEMA,
        "run_id": uuid.uuid4().hex[:12],
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "code_version": code_version(),
        "environment": environment_info(),
        "inputs": source_files,
        "artifacts": artifacts or {},
        "validation_config": asdict(validation_config or ValidationConfig()),
        "validation": {
            "exposure": _validation_block(exposures),
            "claims": _validation_block(claims),
        },
        "study_config": study_config_to_dict(run.study.config),
        "claim_definition": run.study.config.claim_basis_label,
        "current_rate_basis": run.current_rate_basis,
        "study_exclusions": run.study.exclusions.to_dict("records"),
        "assumptions": {"label": a.label, **a.model_dump(mode="json")},
        "results_fingerprint": results_fingerprint(run),
        "output_summary": {
            "segments": int(len(run.results)),
            "blocked_segments": int((run.results["status"] == "BLOCKED").sum()),
            "overall_indicated_rate_pmpm": None
            if pd.isna(overall.indicated_rate_pmpm)
            else float(overall.indicated_rate_pmpm),
            "overall_member_months": float(overall.member_months),
        },
        "warnings": list(run.study.warnings),
        "output_files": output_files or [],
        "output_hashes": {},
    }


def _recompute(
    exposures: pd.DataFrame, claims: pd.DataFrame, manifest: dict
) -> tuple[ValidationResult, ValidationResult, PricingRun]:
    vcfg = ValidationConfig(**manifest.get("validation_config", {}))
    ev = validate_exposure_data(exposures, vcfg)
    cv = validate_claims_data(claims, ev, vcfg)
    study = run_experience_study(
        ev.clean, cv.clean, study_config_from_dict(manifest["study_config"])
    )
    return ev, cv, run_pricing(study, _assumptions_from_manifest(manifest))


def reproduce_run(manifest: dict, exposures: pd.DataFrame, claims: pd.DataFrame) -> dict:
    """Re-run against canonical-named workspace data and compare input and result hashes."""
    checks: dict[str, bool] = {}
    for kind, df in (("exposures", exposures), ("claims", claims)):
        expected = manifest["inputs"].get(kind, {}).get("mapped_data_sha256")
        checks[f"input_{kind}_hash"] = dataframe_fingerprint(df) == expected
    _, _, run = _recompute(exposures, claims, manifest)
    now = results_fingerprint(run)
    for k, v in manifest["results_fingerprint"].items():
        checks[f"result_{k}"] = now.get(k) == v
    return {
        "match": all(checks.values()),
        "checks": checks,
        "code_version_then": manifest["code_version"],
        "code_version_now": code_version(),
    }


def _row(item: str, kind: str, status: str, detail: str = "") -> dict:
    return {"item": item, "kind": kind, "status": status, "detail": detail}


def verify_run_integrity(manifest: dict, store: ArtifactStore, outputs_dir: Path) -> dict:
    """Check that the stored manifest, snapshots and output files are present and unaltered.

    ``manifest`` is the record returned by ``RunRepository.get`` (includes
    ``manifest_sha256``). Returns ``{"ok", "legacy", "checks": DataFrame}``.
    """
    body = {k: v for k, v in manifest.items() if k != "manifest_sha256"}
    rows: list[dict] = []
    recomputed = sha256_bytes(canonical_json(body))
    rows.append(
        _row(
            "manifest (database)",
            "manifest",
            "OK" if recomputed == manifest.get("manifest_sha256") else "CORRUPTED",
        )
    )
    legacy = body.get("manifest_schema", 1) < MANIFEST_SCHEMA
    if legacy:
        rows.append(
            _row(
                "artifact snapshots",
                "legacy",
                "NOT STORED",
                "Run saved before M4.2: no input/cleaned snapshots or output hashes.",
            )
        )
        df = pd.DataFrame(rows)
        return {"ok": False, "legacy": True, "checks": df}

    run_dir = Path(outputs_dir) / body["run_id"]
    mfile = run_dir / "manifest.json"
    if not mfile.is_file():
        rows.append(_row("manifest.json", "manifest", "MISSING", str(mfile)))
    else:
        same = sha256_bytes(mfile.read_bytes()) == manifest.get("manifest_sha256")
        rows.append(_row("manifest.json", "manifest", "OK" if same else "CORRUPTED"))

    for kind, info in body["inputs"].items():
        for key in ("raw_artifact", "mapped_artifact"):
            ref = info.get(key)
            if ref is None:
                detail = (
                    "synthetic input: regenerated from provenance"
                    if key == "raw_artifact"
                    else "no snapshot stored"
                )
                status = "NOT STORED" if key == "raw_artifact" else "MISSING"
                rows.append(_row(f"{kind}.{key}", "input", status, detail))
            else:
                rows.append(_row(f"{kind}.{key}", "input", store.check(ref), ref["sha256"][:16]))
    for name, ref in body.get("artifacts", {}).items():
        rows.append(_row(name, "derived", store.check(ref), ref["sha256"][:16] if ref else ""))
    for name, sha in body.get("output_hashes", {}).items():
        f = run_dir / name
        if not f.is_file():
            rows.append(_row(name, "output", "MISSING", str(f)))
        else:
            ok = sha256_bytes(f.read_bytes()) == sha
            rows.append(_row(name, "output", "OK" if ok else "CORRUPTED", sha[:16]))
    df = pd.DataFrame(rows)
    ok = bool((df["status"].isin(["OK", "NOT STORED"])).all())
    return {"ok": ok, "legacy": False, "checks": df}


def _read_snapshot(data: bytes) -> pd.DataFrame:
    df = pd.read_csv(io.BytesIO(data), dtype=str, keep_default_na=False)
    return df.replace("", pd.NA)


def recalculate_run(manifest: dict, store: ArtifactStore) -> dict:
    """Recompute a saved run from its stored mapped-input snapshots with the current software.

    Returns ``{"match", "checks", "same_environment", "note"}``. Raises ``ArtifactError`` if a
    required snapshot is missing or corrupted (run :func:`verify_run_integrity` first).
    """
    if manifest.get("manifest_schema", 1) < MANIFEST_SCHEMA:
        raise ValueError("Run saved before M4.2 has no input snapshot; recalculation impossible.")
    exp = _read_snapshot(store.read(manifest["inputs"]["exposures"]["mapped_artifact"]))
    clm = _read_snapshot(store.read(manifest["inputs"]["claims"]["mapped_artifact"]))
    ev, cv, run = _recompute(exp, clm, manifest)
    checks: dict[str, bool] = {}
    arts = manifest.get("artifacts", {})
    for name, vr in (("clean_exposures", ev), ("clean_claims", cv)):
        if name in arts:
            checks[f"{name}_hash"] = sha256_bytes(csv_bytes(vr.clean)) == arts[name]["sha256"]
    now = results_fingerprint(run)
    for k, v in manifest["results_fingerprint"].items():
        checks[f"result_{k}"] = now.get(k) == v
    then_env = manifest.get("environment", {})
    now_env = environment_info()
    same_code = manifest["code_version"]["git_commit"] == code_version()["git_commit"]
    same_deps = then_env.get("dependency_fingerprint") == now_env["dependency_fingerprint"]
    same = same_code and same_deps
    note = (
        "Recalculated with the same code commit and dependency fingerprint as the saved run."
        if same
        else "Recalculated with DIFFERENT software than the saved run (code commit and/or "
        "dependencies changed). A match shows current software reproduces the stored results; "
        "it is not a re-execution of the historical environment."
    )
    return {
        "match": all(checks.values()),
        "checks": checks,
        "same_environment": same,
        "same_code": same_code,
        "same_dependencies": same_deps,
        "note": note,
    }
