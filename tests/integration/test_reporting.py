import json
import re
from datetime import date

import pytest

from actuarybench.ingestion.validation import validate_claims_data, validate_exposure_data
from actuarybench.persistence.repositories import RunRepository
from actuarybench.pricing.scenario import run_pricing
from actuarybench.reporting.export import OUTPUT_FILES, save_run
from actuarybench.reporting.manifest import reproduce_run
from actuarybench.schemas.assumptions import AssumptionSet
from actuarybench.studies.segmentation import StudyConfig, run_experience_study
from actuarybench.synthetic import generate_synthetic_dataset
from actuarybench.utils.hashing import dataframe_fingerprint

FORBIDDEN = re.compile(r"compliant|approved|production-ready", re.I)


@pytest.fixture(scope="module")
def pipeline():
    ds = generate_synthetic_dataset()
    ev = validate_exposure_data(ds.exposures)
    cv = validate_claims_data(ds.claims, ev)
    cfg = StudyConfig(
        date(2023, 1, 1),
        date(2025, 12, 31),
        date(2026, 3, 31),
        segment_by=("plan_code", "age_band"),
    )
    study = run_experience_study(ev.clean, cv.clean, cfg)
    a = AssumptionSet(
        name="Base",
        version=1,
        owner="analyst",
        effective_from=date(2026, 1, 1),
        annual_trend=0.08,
        trend_is_illustrative=True,
        elapsed_months=30,
        fixed_expense_pmpm=5_000,
        variable_expense_pct=0.10,
        commission_pct=0.05,
        target_margin_pct=0.05,
        period_weights={2023: 0.2, 2024: 0.3, 2025: 0.5},
    )
    run = run_pricing(study, a)
    files = {
        k: {
            "filename": f"synthetic_{k}",
            "file_sha256": "",
            "mapped_data_sha256": dataframe_fingerprint(df),
        }
        for k, df in (("exposures", ds.exposures), ("claims", ds.claims))
    }
    return ds, ev, cv, run, files


def test_save_run_writes_outputs_and_manifest(pipeline, tmp_path):
    ds, ev, cv, run, files = pipeline
    m = save_run(run, files, ev, cv, tmp_path / "out", tmp_path / "t.db", synthetic=True)
    out = tmp_path / "out" / m["run_id"]
    assert sorted(p.name for p in out.iterdir()) == sorted(OUTPUT_FILES)
    on_disk = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert on_disk["study_config"]["segment_by"] == ["plan_code", "age_band"]
    assert on_disk["assumptions"]["label"] == "Base v1"
    stored = RunRepository(tmp_path / "t.db").get(m["run_id"])
    assert stored["manifest_sha256"] == m["manifest_sha256"]
    report = (out / "report.html").read_text(encoding="utf-8")
    assert m["run_id"] in report and "Synthetic demo data" in report
    assert "ILLUSTRATIVE" in report and "Limitations" in report
    assert not FORBIDDEN.search(report)


def test_reproduce_run_matches(pipeline, tmp_path):
    ds, ev, cv, run, files = pipeline
    m = save_run(run, files, ev, cv, tmp_path / "out", tmp_path / "t.db", synthetic=True)
    stored = RunRepository(tmp_path / "t.db").get(m["run_id"])
    r = reproduce_run(stored, ds.exposures, ds.claims)
    assert r["match"], r["checks"]


def test_reproduce_run_detects_changed_input(pipeline, tmp_path):
    ds, ev, cv, run, files = pipeline
    m = save_run(run, files, ev, cv, tmp_path / "out", tmp_path / "t.db", synthetic=True)
    claims = ds.claims.copy()
    claims.loc[0, "paid_amount"] += 1_000
    claims.loc[0, "incurred_amount"] += 1_000
    r = reproduce_run(RunRepository(tmp_path / "t.db").get(m["run_id"]), ds.exposures, claims)
    assert not r["match"]
    assert r["checks"]["input_claims_hash"] is False


def test_runs_are_immutable(pipeline, tmp_path):
    import sqlite3

    ds, ev, cv, run, files = pipeline
    m = save_run(run, files, ev, cv, tmp_path / "out", tmp_path / "t.db", synthetic=True)
    with (
        pytest.raises(sqlite3.DatabaseError, match="immutable"),
        sqlite3.connect(tmp_path / "t.db") as c,
    ):
        c.execute("UPDATE runs SET manifest = '{}' WHERE run_id = ?", (m["run_id"],))
