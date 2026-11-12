"""M4.2 Issue 4 — saved runs carry snapshots; integrity and recalculation after restart."""

import json
import os
import stat
import subprocess
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from actuarybench.ingestion.mapping import apply_mapping, suggest_mapping
from actuarybench.ingestion.readers import read_table
from actuarybench.ingestion.validation import validate_claims_data, validate_exposure_data
from actuarybench.persistence.artifacts import ArtifactError, ArtifactStore
from actuarybench.persistence.repositories import RunRepository
from actuarybench.pricing.scenario import run_pricing
from actuarybench.reporting.export import save_run
from actuarybench.reporting.manifest import recalculate_run, verify_run_integrity
from actuarybench.schemas.assumptions import AssumptionSet
from actuarybench.schemas.canonical import CLAIM_FIELDS, EXPOSURE_FIELDS
from actuarybench.studies.segmentation import StudyConfig, run_experience_study
from actuarybench.synthetic import generate_invalid_fixture, generate_synthetic_dataset
from actuarybench.utils.hashing import dataframe_fingerprint, sha256_bytes

ROOT = Path(__file__).resolve().parents[2]
SYN = ROOT / "data" / "synthetic"
A = AssumptionSet(
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
CFG = StudyConfig(
    date(2023, 1, 1), date(2025, 12, 31), date(2026, 3, 31), segment_by=("plan_code",)
)


def _uploaded(name: str, fields):
    content = (SYN / name).read_bytes()
    t = read_table(name, content)
    m = suggest_mapping(list(t.data.columns), fields)
    mapped = apply_mapping(t.data, m)
    info = {
        "filename": name,
        "file_sha256": t.sha256,
        "mapped_data_sha256": dataframe_fingerprint(mapped),
        "mapping": m,
    }
    return mapped, info, content


def _save(tmp_path, exposures, claims, files, raw, assumptions=A, cfg=CFG):
    ev = validate_exposure_data(exposures)
    cv = validate_claims_data(claims, ev)
    run = run_pricing(run_experience_study(ev.clean, cv.clean, cfg), assumptions)
    return save_run(
        run,
        files,
        ev,
        cv,
        tmp_path / "out",
        tmp_path / "t.db",
        synthetic=False,
        mapped={"exposures": exposures, "claims": claims},
        raw_files=raw,
    )


@pytest.fixture
def saved(tmp_path):
    me, ie, re_ = _uploaded("demo_exposures.csv", EXPOSURE_FIELDS)
    mc, ic, rc = _uploaded("demo_claims.csv", CLAIM_FIELDS)
    m = _save(
        tmp_path,
        me,
        mc,
        {"exposures": ie, "claims": ic},
        {"exposures": (".csv", re_), "claims": (".csv", rc)},
    )
    store = ArtifactStore(tmp_path / "artifacts")
    return tmp_path, m, store, RunRepository(tmp_path / "t.db").get(m["run_id"])


def test_manifest_contents(saved):
    tmp_path, m, store, rec = saved
    assert rec["manifest_schema"] == 2
    for kind in ("exposures", "claims"):
        assert store.check(rec["inputs"][kind]["raw_artifact"]) == "OK"
        assert store.check(rec["inputs"][kind]["mapped_artifact"]) == "OK"
        # the mapped snapshot *is* the hashed mapped input
        assert (
            rec["inputs"][kind]["mapped_artifact"]["sha256"]
            == rec["inputs"][kind]["mapped_data_sha256"]
        )
        assert rec["inputs"][kind]["mapping"]
    assert set(rec["artifacts"]) == {"clean_exposures", "clean_claims", "validation_issues"}
    assert rec["validation_config"] == {"incurred_tolerance": 1.0, "member_month_tolerance": 0.5}
    assert rec["code_version"]["method"] == "method-0.2.0"
    env = rec["environment"]
    assert env["python"] and env["packages"]["pandas"] and len(env["dependency_fingerprint"]) == 64
    assert rec["current_rate_basis"] == "latest_experience_period_full_coverage"
    assert set(rec["output_hashes"]) == {"report.html", "results.xlsx", "pricing_results.csv"}
    disk = (tmp_path / "out" / m["run_id"] / "manifest.json").read_bytes()
    assert sha256_bytes(disk) == rec["manifest_sha256"]


def test_integrity_ok(saved):
    tmp_path, _, store, rec = saved
    r = verify_run_integrity(rec, store, tmp_path / "out")
    assert r["ok"] and not r["legacy"], r["checks"]
    assert set(r["checks"]["status"]) == {"OK"}


def test_reopen_verify_and_recalculate_in_fresh_process(saved):
    tmp_path, m, _, _ = saved
    script = f"""
import json, sys
sys.path.insert(0, {str(ROOT / "src")!r})
from pathlib import Path
from actuarybench.persistence.artifacts import ArtifactStore
from actuarybench.persistence.repositories import RunRepository
from actuarybench.reporting.manifest import recalculate_run, verify_run_integrity
tmp = Path({str(tmp_path)!r})
rec = RunRepository(tmp / "t.db").get({m["run_id"]!r})
store = ArtifactStore(tmp / "artifacts")
i = verify_run_integrity(rec, store, tmp / "out")
r = recalculate_run(rec, store)
print(json.dumps({{"integrity": i["ok"], "match": r["match"], "checks": r["checks"],
                  "same_environment": r["same_environment"]}}))
"""
    out = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, timeout=300, check=True
    )
    res = json.loads(out.stdout.strip().splitlines()[-1])
    assert res["integrity"] is True
    assert res["match"] is True, res["checks"]
    assert res["checks"]["clean_exposures_hash"] and res["checks"]["clean_claims_hash"]


def _make_writable(p: Path) -> None:
    os.chmod(p, stat.S_IREAD | stat.S_IWRITE)


def test_corrupted_input_artifact_detected(saved):
    tmp_path, _, store, rec = saved
    p = store.path_for(rec["inputs"]["claims"]["mapped_artifact"])
    _make_writable(p)
    p.write_bytes(p.read_bytes().replace(b"CLM0000001", b"CLM9999999"))
    r = verify_run_integrity(rec, store, tmp_path / "out")
    assert not r["ok"]
    row = r["checks"].set_index("item").loc["claims.mapped_artifact"]
    assert row.status == "CORRUPTED"
    with pytest.raises(ArtifactError, match="CORRUPTED"):
        recalculate_run(rec, store)


def test_missing_artifact_and_output_detected(saved):
    tmp_path, m, store, rec = saved
    p = store.path_for(rec["artifacts"]["clean_claims"])
    _make_writable(p)
    p.unlink()
    (tmp_path / "out" / m["run_id"] / "report.html").unlink()
    checks = verify_run_integrity(rec, store, tmp_path / "out")["checks"].set_index("item")
    assert checks.loc["clean_claims", "status"] == "MISSING"
    assert checks.loc["report.html", "status"] == "MISSING"


def test_tampered_outputs_and_manifest_detected(saved):
    tmp_path, m, store, rec = saved
    run_dir = tmp_path / "out" / m["run_id"]
    csv = run_dir / "pricing_results.csv"
    csv.write_text(csv.read_text().replace("OK", "XX", 1))
    mf = run_dir / "manifest.json"
    mf.write_bytes(mf.read_bytes().replace(b'"Base"', b'"Edit"', 1))
    checks = verify_run_integrity(rec, store, tmp_path / "out")["checks"].set_index("item")
    assert checks.loc["pricing_results.csv", "status"] == "CORRUPTED"
    assert checks.loc["manifest.json", "status"] == "CORRUPTED"
    forged = {**rec, "assumptions": {**rec["assumptions"], "owner": "someone else"}}
    checks = verify_run_integrity(forged, store, tmp_path / "out")["checks"].set_index("item")
    assert checks.loc["manifest (database)", "status"] == "CORRUPTED"


def test_different_software_is_reported(saved):
    _, _, store, rec = saved
    other = {**rec, "environment": {**rec["environment"], "dependency_fingerprint": "0" * 64}}
    r = recalculate_run(other, store)
    assert r["match"] and not r["same_environment"]
    assert "DIFFERENT software" in r["note"]


def test_legacy_run_reported(saved):
    tmp_path, _, store, rec = saved
    legacy = {k: v for k, v in rec.items() if k != "manifest_schema"}
    r = verify_run_integrity(legacy, store, tmp_path / "out")
    assert r["legacy"] and not r["ok"]
    with pytest.raises(ValueError, match="before M4.2"):
        recalculate_run(legacy, store)


def test_synthetic_typed_input_recalculates(tmp_path):
    ds = generate_synthetic_dataset()
    files = {
        k: {
            "filename": f"synthetic_{k}",
            "file_sha256": "",
            "mapped_data_sha256": dataframe_fingerprint(df),
            "provenance": {"seed": 1},
        }
        for k, df in (("exposures", ds.exposures), ("claims", ds.claims))
    }
    m = _save(tmp_path, ds.exposures, ds.claims, files, None)
    rec = RunRepository(tmp_path / "t.db").get(m["run_id"])
    store = ArtifactStore(tmp_path / "artifacts")
    integ = verify_run_integrity(rec, store, tmp_path / "out")
    assert integ["ok"], integ["checks"]
    raw_rows = integ["checks"][integ["checks"]["item"].str.endswith("raw_artifact")]
    assert set(raw_rows["status"]) == {"NOT STORED"}
    assert recalculate_run(rec, store)["match"]


def test_excluded_row_details_persisted(tmp_path):
    bad = generate_invalid_fixture()
    exp = bad.exposures.drop(columns="_defect").astype("string")
    clm = bad.claims.drop(columns="_defect").astype("string")
    exp = exp.where(exp != "None", pd.NA)
    clm = clm.where(clm != "None", pd.NA)
    files = {
        k: {"filename": k, "file_sha256": "", "mapped_data_sha256": dataframe_fingerprint(df)}
        for k, df in (("exposures", exp), ("claims", clm))
    }
    a = A.model_copy(update={"period_weights": {2025: 1.0}})
    cfg = StudyConfig(date(2025, 1, 1), date(2025, 12, 31), date(2026, 3, 31))
    m = _save(tmp_path, exp, clm, files, None, assumptions=a, cfg=cfg)
    store = ArtifactStore(tmp_path / "artifacts")
    import io

    issues = pd.read_csv(io.BytesIO(store.read(m["artifacts"]["validation_issues"])))
    errors = issues[issues["severity"] == "ERROR"]
    assert {"orphan_claim", "duplicate_claim_id", "duplicate_exposure_id"} <= set(errors["code"])
    assert "C4" in set(errors["record_id"])
    clean = pd.read_csv(io.BytesIO(store.read(m["artifacts"]["clean_claims"])))
    assert sorted(clean["claim_id"]) == ["C1", "C3"]
