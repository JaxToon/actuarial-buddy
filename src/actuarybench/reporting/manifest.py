"""Run manifests and reproducibility verification (docs/ACTUARIAL_METHODS.md §12)."""

from __future__ import annotations

import subprocess
import uuid
from dataclasses import asdict
from datetime import UTC, date, datetime

import pandas as pd

import actuarybench
from actuarybench.config import PROJECT_ROOT
from actuarybench.ingestion.validation import (
    ValidationResult,
    validate_claims_data,
    validate_exposure_data,
)
from actuarybench.pricing.scenario import PricingRun, run_pricing
from actuarybench.schemas.assumptions import AssumptionSet
from actuarybench.studies.segmentation import StudyConfig, run_experience_study
from actuarybench.utils.hashing import dataframe_fingerprint


def code_version() -> dict:
    """Package/method version and git commit when available (``-dirty`` if uncommitted)."""
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
            ["git", "status", "--porcelain", "--", "src"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()
        out["git_commit"] = commit.strip() + ("-dirty" if dirty else "")
    except (OSError, subprocess.SubprocessError):
        pass
    return out


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


def build_run_manifest(
    run: PricingRun,
    source_files: dict[str, dict],
    exposures: ValidationResult,
    claims: ValidationResult,
    output_files: list[str] | None = None,
) -> dict:
    a: AssumptionSet = run.assumptions
    overall = run.results[run.results["segment"] == "ALL"].iloc[0]
    return {
        "run_id": uuid.uuid4().hex[:12],
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "code_version": code_version(),
        "inputs": source_files,
        "validation": {
            "exposure": _validation_block(exposures),
            "claims": _validation_block(claims),
        },
        "study_config": study_config_to_dict(run.study.config),
        "claim_definition": run.study.config.claim_basis_label,
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
    }


def reproduce_run(manifest: dict, exposures: pd.DataFrame, claims: pd.DataFrame) -> dict:
    """Re-run validation → study → pricing from canonical-named inputs and compare result
    fingerprints with the manifest. Returns a dict with ``match`` and per-check details."""
    checks: dict[str, bool] = {}
    for kind, df in (("exposures", exposures), ("claims", claims)):
        expected = manifest["inputs"].get(kind, {}).get("mapped_data_sha256")
        checks[f"input_{kind}_hash"] = dataframe_fingerprint(df) == expected
    ev = validate_exposure_data(exposures)
    cv = validate_claims_data(claims, ev)
    study = run_experience_study(
        ev.clean, cv.clean, study_config_from_dict(manifest["study_config"])
    )
    a_payload = {k: v for k, v in manifest["assumptions"].items() if k != "label"}
    a_payload["period_weights"] = {int(k): v for k, v in a_payload["period_weights"].items()}
    run = run_pricing(study, AssumptionSet.model_validate(a_payload))
    now = results_fingerprint(run)
    for k, v in manifest["results_fingerprint"].items():
        checks[f"result_{k}"] = now.get(k) == v
    return {
        "match": all(checks.values()),
        "checks": checks,
        "code_version_then": manifest["code_version"],
        "code_version_now": code_version(),
    }
