"""Run history, report downloads, artifact integrity and recalculation."""

from __future__ import annotations

import json

import pandas as pd
import streamlit as st
from ui.state import artifacts_dir, db_path, get_validation, outputs_dir, synthetic_banner

from actuarybench.persistence.artifacts import ArtifactError, ArtifactStore
from actuarybench.persistence.repositories import RunRepository
from actuarybench.reporting.export import save_run
from actuarybench.reporting.manifest import recalculate_run, reproduce_run, verify_run_integrity

MIME = {
    ".html": "text/html",
    ".csv": "text/csv",
    ".json": "application/json",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

st.header("Run history & reports")
synthetic_banner()
repo = RunRepository(db_path())
out_dir = outputs_dir()
store = ArtifactStore(artifacts_dir())
st.caption(
    f"Local artifact store: `{store.root}` — content-addressed, tamper-evident, single-user. "
    "Not access-controlled or encrypted; not suitable for sensitive insurer data."
)


def download_buttons(manifest: dict, key: str) -> None:
    out = out_dir / manifest["run_id"]
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


def checks_table(checks: dict[str, bool]) -> None:
    st.dataframe(
        pd.DataFrame([{"check": k, "passed": v} for k, v in checks.items()]), hide_index=True
    )


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
                out_dir,
                db_path(),
                synthetic=st.session_state.get("data_source") == "synthetic",
                mapped={k: st.session_state[f"mapped_{k}"] for k in ("exposures", "claims")},
                raw_files={
                    k: st.session_state.get(f"raw_upload_{k}") for k in ("exposures", "claims")
                },
                artifacts_dir=store.root,
            )
            st.success(
                f"Saved run {m['run_id']} (manifest SHA-256 {m['manifest_sha256'][:12]}…) with "
                "input, cleaned-data and exclusion snapshots.",
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
            "snapshots": "yes" if m.get("manifest_schema", 1) >= 2 else "no (pre-M4.2)",
            "method": m["code_version"]["method"],
            "git_commit": m["code_version"]["git_commit"][:12],
        }
        for m in history
    ]
)
st.dataframe(
    table.style.format({"overall_indicated_rate_pmpm": "{:,.0f}"}, na_rep="N/A"),
    hide_index=True,
)

run_id = st.selectbox("Inspect run", [m["run_id"] for m in history])
m = next(x for x in history if x["run_id"] == run_id)
with st.container(border=True):
    download_buttons(m, "hist")
    with st.expander("Manifest"):
        st.json(json.loads(json.dumps(m, default=str)), expanded=1)

    st.markdown(
        "**1 · Artifact integrity** — are the stored manifest, input/cleaned snapshots, "
        "exclusion details and output files present and unaltered? (No recalculation.)"
    )
    if st.button("Check artifact integrity", icon=":material/verified_user:"):
        r = verify_run_integrity(m, store, out_dir)
        if r["legacy"]:
            st.warning("Run saved before M4.2 — no snapshots to verify.", icon=":material/info:")
        elif r["ok"]:
            st.success(
                "Integrity verified: all artifacts present and unaltered.",
                icon=":material/check:",
            )
        else:
            st.error(
                "Integrity FAILED — missing or corrupted artifacts listed below.",
                icon=":material/error:",
            )
        st.dataframe(r["checks"], hide_index=True)

    st.markdown(
        "**2 · Recalculate from stored snapshots** — re-runs validation, study and pricing from "
        "the saved input snapshot with the currently installed software."
    )
    if st.button("Recalculate from stored artifacts", icon=":material/replay:"):
        try:
            r = recalculate_run(m, store)
        except (ArtifactError, ValueError) as exc:
            st.error(f"Cannot recalculate: {exc}", icon=":material/error:")
        else:
            if r["match"]:
                st.success("Recalculated results match the saved run.", icon=":material/check:")
            else:
                st.error("Recalculated results DIFFER from the saved run.", icon=":material/error:")
            (st.info if r["same_environment"] else st.warning)(r["note"])
            checks_table(r["checks"])

    st.markdown(
        "**3 · Compare with current workspace data** — re-runs on the data loaded now and "
        "compares input and result hashes."
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
            checks_table(r["checks"])
