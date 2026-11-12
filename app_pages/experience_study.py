"""Study setup & experience study results page."""

from __future__ import annotations

from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st
from ui.format import format_metrics_table
from ui.state import get_validation, synthetic_banner

from actuarybench.config import DEFAULT_LOW_EXPOSURE_THRESHOLD_MM
from actuarybench.studies.segmentation import (
    SEGMENT_CANDIDATES,
    StudyConfig,
    StudyConfigError,
    run_experience_study,
)

st.header("Experience study")
synthetic_banner()

res = get_validation()
if res is None or not (res[0].ok and res[1].ok):
    st.warning("Load, map and validate exposure and claims data first.")
    st.stop()
ev, cv = res
exp, clm = ev.clean, cv.clean
if exp.empty:
    st.error("No valid exposure rows after validation.")
    st.stop()

min_d = exp["coverage_start"].min().date()
max_d = exp["coverage_end"].max().date()
dims = [d for d in SEGMENT_CANDIDATES if d in exp.columns]
has_incurred = "incurred_amount" in clm.columns

with st.form("study_setup"), st.container(border=True):
    st.subheader("Study setup")
    c1, c2, c3 = st.columns(3)
    period = c1.date_input("Study period", (min_d, max_d), min_value=date(1990, 1, 1))
    evaluation = c2.date_input(
        "Evaluation date",
        max(max_d, clm["reported_date"].max().date())
        if "reported_date" in clm and clm["reported_date"].notna().any()
        else max_d,
        help="Claims reported after this date are excluded.",
    )
    basis = c3.radio(
        "Claim basis",
        ["incurred", "paid"] if has_incurred else ["paid"],
        format_func={"incurred": "Incurred (paid + case reserve)", "paid": "Paid only"}.get,
    )
    c4, c5 = st.columns([2, 1])
    segment_by = c4.multiselect(
        "Segment by",
        dims,
        default=[d for d in ("plan_code",) if d in dims],
        help="Configurable segmentation. Sensitive attributes are never mandatory.",
    )
    threshold = c5.number_input(
        "Low-exposure threshold (member-months)",
        min_value=0.0,
        value=DEFAULT_LOW_EXPOSURE_THRESHOLD_MM,
        step=100.0,
        help="Segments below this are flagged for review. Not a credibility method.",
    )
    run = st.form_submit_button(
        "Run experience study", type="primary", icon=":material/play_arrow:"
    )

if run:
    if not isinstance(period, tuple) or len(period) != 2:
        st.error("Select both a start and an end date for the study period.")
        st.stop()
    cfg = StudyConfig(
        period_start=period[0],
        period_end=period[1],
        evaluation_date=evaluation,
        claim_basis=basis,
        segment_by=tuple(segment_by),
        low_exposure_threshold_mm=threshold,
    )
    try:
        st.session_state.study_result = run_experience_study(exp, clm, cfg)
    except StudyConfigError as exc:
        st.error(str(exc), icon=":material/error:")
        st.stop()

result = st.session_state.get("study_result")
if result is None:
    st.info("Configure the study and press **Run experience study**.")
    st.stop()

cfg = result.config
seg_label = ", ".join(cfg.segment_by) or "none (overall only)"
st.markdown(
    f"**Period** {cfg.period_start:%Y-%m-%d} → {cfg.period_end:%Y-%m-%d} · "
    f"**Evaluation date** {cfg.evaluation_date:%Y-%m-%d} · **Segments** {seg_label}  \n"
    f"**Claim definition** {cfg.claim_basis_label} · **Grain** one row per claim; exposure in "
    f"member-months · **Currency** IDR"
)
for w in result.warnings:
    st.warning(w, icon=":material/warning:")

o = result.overall.iloc[0]
with st.container(horizontal=True):
    st.metric(
        "Earned member-months",
        f"{o.earned_member_months:,.0f}",
        help=f"= {o.member_years:,.1f} member-years",
        border=True,
    )
    st.metric("Claims (count)", f"{o.claim_count:,}", border=True)
    st.metric(
        "Frequency / 1,000 member-years",
        f"{o.frequency_per_1000_my:,.1f}",
        border=True,
        help="claims ÷ (member-months ÷ 12) × 1,000",
    )
    st.metric(
        "Average severity (IDR)",
        "N/A" if pd.isna(o.average_severity) else f"{o.average_severity:,.0f}",
        border=True,
        help="claim amount ÷ claim count",
    )
    st.metric(
        "Claim cost PMPM (IDR)",
        f"{o.claim_cost_pmpm:,.0f}",
        border=True,
        help="claim amount ÷ member-months",
    )
    st.metric(
        "Loss ratio",
        "N/A" if pd.isna(o.loss_ratio) else f"{o.loss_ratio:.1%}",
        border=True,
        help="claim amount ÷ earned premium",
    )

tab_seg, tab_period, tab_ps, tab_excl = st.tabs(
    ["By segment", "By experience period", "Period × segment", "Study exclusions"]
)
with tab_seg:
    st.caption(f"One row per segment ({seg_label}). Denominators shown in each row.")
    st.dataframe(format_metrics_table(result.by_segment), hide_index=True)
    if cfg.segment_by:
        dim = cfg.segment_by[0]
        fig = px.bar(
            result.by_segment,
            x=dim,
            y="claim_cost_pmpm",
            color=cfg.segment_by[1] if len(cfg.segment_by) > 1 else None,
            barmode="group",
            labels={"claim_cost_pmpm": "Claim cost PMPM (IDR)"},
            title=(
                f"Claim cost PMPM by {seg_label} · {cfg.period_start:%Y-%m-%d} to "
                f"{cfg.period_end:%Y-%m-%d} · denominator: member-months"
            ),
        )
        st.plotly_chart(fig)
with tab_period:
    st.caption("Experience period = calendar year of coverage start.")
    st.dataframe(format_metrics_table(result.by_period), hide_index=True)
with tab_ps:
    st.dataframe(format_metrics_table(result.by_period_segment), hide_index=True)
with tab_excl:
    st.caption("Rows that passed validation but fall outside this study's definition.")
    st.dataframe(result.exclusions, hide_index=True)
    st.caption(
        f"Used: {result.exposure_rows_used:,} exposure rows, {result.claim_rows_used:,} claim rows."
    )
