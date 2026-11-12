"""Validation results page."""

from __future__ import annotations

import pandas as pd
import streamlit as st
from ui.state import get_validation, synthetic_banner

from actuarybench.ingestion.validation import validation_summary
from actuarybench.reporting.workbook import to_xlsx_bytes, validation_report_sheets

st.header("Validation results")
synthetic_banner()

res = get_validation()
if res is None:
    st.warning("Load or map both an exposure and a claims dataset first.")
    st.stop()
ev, cv = res

for r in (ev, cv):
    for msg in r.schema_errors:
        st.error(f"{r.record_type}: {msg}", icon=":material/error:")
if not (ev.ok and cv.ok):
    st.stop()

with st.container(horizontal=True):
    st.metric("Valid exposure rows", f"{ev.rows_out:,} / {ev.rows_in:,}", border=True)
    st.metric("Valid claim rows", f"{cv.rows_out:,} / {cv.rows_in:,}", border=True)
    n_err = int((ev.issues.severity == "ERROR").sum() + (cv.issues.severity == "ERROR").sum())
    n_warn = int((ev.issues.severity == "WARNING").sum() + (cv.issues.severity == "WARNING").sum())
    st.metric("Error issues", f"{n_err:,}", border=True)
    st.metric("Warning issues", f"{n_warn:,}", border=True)

if ev.rows_excluded == 0 and cv.rows_excluded == 0:
    st.success("Valid — no rows excluded.", icon=":material/check_circle:")
else:
    st.warning(
        f"{ev.rows_excluded:,} exposure rows and {cv.rows_excluded:,} claim rows are excluded. "
        "Each exclusion is listed below with its reason.",
        icon=":material/warning:",
    )
for d in cv.derivations:
    st.info(f"Derivation applied: {d}", icon=":material/function:")

st.dataframe(validation_summary([ev, cv]), hide_index=True)

for r in (ev, cv):
    with st.container(border=True):
        st.subheader(r.record_type.capitalize())
        c1, c2 = st.columns(2)
        c1.markdown("**Reconciliation (before → after exclusions)**")
        c1.dataframe(r.reconciliation(), hide_index=True)
        c2.markdown("**Exclusions by reason (rows)**")
        c2.dataframe(r.excluded_by_reason(), hide_index=True)
        c2.markdown("**Warnings by reason (rows kept)**")
        c2.dataframe(r.warnings_by_reason(), hide_index=True)
        with st.expander(f"All {r.record_type} issues ({len(r.issues):,})"):
            sev = st.segmented_control(
                "Severity",
                ["ERROR", "WARNING"],
                selection_mode="multi",
                default=["ERROR", "WARNING"],
                key=f"sev_{r.record_type}",
            )
            st.dataframe(r.issues[r.issues.severity.isin(sev or [])], hide_index=True)

sheets = validation_report_sheets([ev, cv], st.session_state.get("source_files"))
with st.container(horizontal=True):
    st.download_button(
        "Download validation report (XLSX)",
        to_xlsx_bytes(sheets),
        file_name="validation_report.xlsx",
        icon=":material/download:",
        type="primary",
    )
    issues_csv = pd.concat([ev.issues, cv.issues]).to_csv(index=False).encode()
    st.download_button(
        "Download all issues (CSV)",
        issues_csv,
        file_name="validation_issues.csv",
        icon=":material/download:",
    )
