"""Run history, report downloads and reproducibility verification."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st
from ui.state import db_path, get_validation, synthetic_banner

from actuarybench.config import OUTPUTS_DIR
from actuarybench.persistence.repositories import RunRepository
from actuarybench.reporting.export import save_run
from actuarybench.reporting.manifest import reproduce_run

MIME = {
    ".html": "text/html",
    ".csv": "text/csv",
    ".json": "application/json",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

st.header("Run history & reports")
synthetic_banner()
repo = RunRepository(db_path())
outputs_dir = Path(st.session_state.get("outputs_dir", OUTPUTS_DIR))


def download_buttons(manifest: dict, key: str) -> None:
    out = outputs_dir / manifest["run_id"]
    with st.container(horizontal=True):
        for name in manifest.get("output_files", []):
            f = out / name
            if f.exists():
                st.download_button(
                    name,
                    f.read_bytes(),
                    file_name=f"{manifest['run_id']}_{name}",
                    mime=MIME.get(f.suffix),
                    icon=":material/download:",
                    key=f"dl_{key}_{name}",
                )
            else:
                st.caption(f"{name} missing from {out}")


runs = st.session_state.get("pricing_runs") or []
with st.container(border=True):
    st.subheader("Save current results as a run")
    if not runs:
        st.info("Run a pricing indication first (Assumptions & pricing page).")
    res = get_validation()
    for i, run in enumerate(runs):
        c1, c2 = st.columns([3, 1])
        c1.markdown(f"**{run.assumptions.label}** · {len(run.results)} segment rows")
        if c2.button("Save run & generate report", key=f"save_{i}", icon=":material/save:"):
            m = save_run(
                run,
                st.session_state.source_files,
                res[0],
                res[1],
                outputs_dir,
                db_path(),
                synthetic=st.session_state.get("data_source") == "synthetic",
            )
            st.success(
                f"Saved run {m['run_id']} (manifest SHA-256 {m['manifest_sha256'][:12]}…).",
                icon=":material/check:",
            )
            download_buttons(m, f"new_{i}")

history = repo.list()
st.subheader(f"Run history ({len(history)})")
if not history:
    st.caption("No saved runs yet.")
    st.stop()

table = pd.DataFrame(
    [
        {
            "run_id": m["run_id"],
            "created_at (UTC)": m["created_at"],
            "assumptions": m["assumptions"]["label"],
            "study_period": " → ".join(
                m["study_config"][k] for k in ("period_start", "period_end")
            ),
            "segments": ", ".join(m["study_config"]["segment_by"]) or "overall",
            "overall_indicated_rate_pmpm": m["output_summary"]["overall_indicated_rate_pmpm"],
            "blocked_segments": m["output_summary"]["blocked_segments"],
            "git_commit": m["code_version"]["git_commit"][:12],
        }
        for m in history
    ]
)
st.dataframe(
    table.style.format({"overall_indicated_rate_pmpm": "{:,.0f}"}, na_rep="N/A"), hide_index=True
)

run_id = st.selectbox("Inspect run", [m["run_id"] for m in history])
m = next(x for x in history if x["run_id"] == run_id)
with st.container(border=True):
    download_buttons(m, "hist")
    with st.expander("Manifest"):
        st.json(json.loads(json.dumps(m, default=str)), expanded=1)
    st.markdown(
        "**Reproducibility check** — re-runs validation, study and pricing on the data "
        "currently loaded in this workspace and compares input and result hashes."
    )
    if st.button("Verify against current workspace data", icon=":material/verified:"):
        if "mapped_exposures" not in st.session_state:
            st.error("No data loaded.")
        else:
            r = reproduce_run(m, st.session_state.mapped_exposures, st.session_state.mapped_claims)
            if r["match"]:
                st.success("Reproduced: identical inputs and results.", icon=":material/check:")
            else:
                st.error("Not reproduced — see failing checks.", icon=":material/error:")
            st.dataframe(
                pd.DataFrame([{"check": k, "passed": v} for k, v in r["checks"].items()]),
                hide_index=True,
            )
            st.caption(
                f"Code then: {r['code_version_then']['git_commit'][:12]} · "
                f"now: {r['code_version_now']['git_commit'][:12]}"
            )
