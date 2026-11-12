"""Assumption sets, scenario builder and pricing indication results."""

from __future__ import annotations

from datetime import date

import streamlit as st
from pydantic import ValidationError
from ui.state import db_path, synthetic_banner

from actuarybench.persistence.repositories import AssumptionRepository, DuplicateVersionError
from actuarybench.pricing.scenario import BLOCKED, compare_scenarios, run_pricing
from actuarybench.pricing.trend import suggest_elapsed_months
from actuarybench.schemas.assumptions import AssumptionSet

st.header("Assumptions & pricing indication")
synthetic_banner()

study = st.session_state.get("study_result")
if study is None:
    st.warning("Run an experience study first.")
    st.stop()

repo = AssumptionRepository(db_path())
periods = sorted(int(p) for p in study.by_period["experience_period"])
cfg = study.config
st.caption(
    f"Study: {cfg.period_start:%Y-%m-%d} → {cfg.period_end:%Y-%m-%d} · evaluation "
    f"{cfg.evaluation_date:%Y-%m-%d} · segments {', '.join(cfg.segment_by) or 'overall'} · "
    f"{cfg.claim_basis_label}"
)

tab_new, tab_run = st.tabs(["New assumption set", "Run & compare scenarios"])

with tab_new:
    with st.container(border=True):
        st.markdown("**Projection period** (used only to *suggest* elapsed months)")
        c1, c2 = st.columns(2)
        proj = c1.date_input(
            "Projection period",
            (date(cfg.period_end.year + 2, 1, 1), date(cfg.period_end.year + 2, 12, 31)),
        )
        if isinstance(proj, tuple) and len(proj) == 2:
            suggestion = suggest_elapsed_months(cfg.period_start, cfg.period_end, *proj)
            c2.metric(
                "Suggested elapsed months",
                f"{suggestion:.1f}",
                help="Study-period midpoint → projection-period midpoint. Confirm or "
                "override below; year-weighted experience may justify a different value.",
            )
        else:
            suggestion = 12.0

    with st.form("new_assumptions"):
        c1, c2, c3 = st.columns(3)
        name = c1.text_input("Name", "Base")
        owner = c2.text_input("Owner", "analyst")
        eff_from = c3.date_input("Effective from", date.today())
        notes = st.text_area("Notes / source / rationale", height=80)

        st.markdown("**Trend**")
        t1, t2, t3, t4 = st.columns(4)
        trend_pct = t1.number_input("Annual medical trend (%)", -50.0, 100.0, 10.0, 0.5)
        elapsed = t2.number_input("Elapsed months", 0.0, 120.0, round(suggestion, 1), 0.5)
        trend_source = t3.text_input("Trend source", "")
        illustrative = t4.checkbox(
            "Trend is illustrative only",
            value=True,
            help="Shown as a warning on every result and report.",
        )

        st.markdown("**Loadings** (percent of gross premium; fixed expense in IDR PMPM)")
        l1, l2, l3, l4 = st.columns(4)
        fixed = l1.number_input("Fixed admin expense (IDR PMPM)", 0.0, value=5_000.0, step=500.0)
        var_pct = l2.number_input("Variable expense (%)", 0.0, 99.0, 10.0, 0.5)
        com_pct = l3.number_input("Commission (%)", 0.0, 99.0, 5.0, 0.5)
        mar_pct = l4.number_input("Target margin (%)", 0.0, 99.0, 5.0, 0.5)

        st.markdown("**Experience-period weighting**")
        method = st.radio(
            "Method",
            ["year_weighted", "exposure_weighted"],
            horizontal=True,
            format_func={
                "year_weighted": "Year-weighted Σ wₜ·PPₜ",
                "exposure_weighted": "Exposure-weighted ΣC / ΣE",
            }.get,
        )
        equal = round(100.0 / len(periods), 4)
        wcols = st.columns(len(periods))
        weights_pct = {
            p: wcols[i].number_input(f"Weight {p} (%)", 0.0, 100.0, equal, 1.0, key=f"w_{p}")
            for i, p in enumerate(periods)
        }
        confirm_equal = st.checkbox(
            "I confirm the default equal weights are intended",
            help="Required if you keep the default equal weights.",
        )
        saved = st.form_submit_button("Save new assumption set version", type="primary")

    if saved:
        weights = {p: w / 100.0 for p, w in weights_pct.items()}
        if method == "year_weighted":
            if all(abs(w - equal) < 1e-9 for w in weights_pct.values()) and not confirm_equal:
                st.error("Confirm the default equal weights, or enter explicit weights.")
                st.stop()
            total = sum(weights.values())
            if abs(total - 1.0) < 1e-3:  # tolerate UI rounding (e.g. 33.3333 × 3)
                weights = {p: w / total for p, w in weights.items()}
        try:
            a = AssumptionSet(
                name=name,
                version=repo.next_version(name.strip()),
                owner=owner,
                effective_from=eff_from,
                notes=notes,
                annual_trend=trend_pct / 100,
                trend_source=trend_source,
                trend_is_illustrative=illustrative,
                elapsed_months=elapsed,
                fixed_expense_pmpm=fixed,
                variable_expense_pct=var_pct / 100,
                commission_pct=com_pct / 100,
                target_margin_pct=mar_pct / 100,
                weighting_method=method,
                period_weights=weights if method == "year_weighted" else {},
            )
            repo.save(a)
            st.success(f"Saved {a.label}. Saved sets are immutable.", icon=":material/check:")
        except ValidationError as exc:
            for err in exc.errors():
                st.error(f"{'.'.join(map(str, err['loc'])) or 'assumptions'}: {err['msg']}")
        except DuplicateVersionError as exc:
            st.error(str(exc))

with tab_run:
    sets = repo.list()
    if not sets:
        st.info("Save an assumption set first.")
        st.stop()
    by_label = {a.label: a for a in sets}
    chosen = st.multiselect(
        "Scenarios (first = base)",
        list(by_label),
        default=[list(by_label)[-1]],
        help="Each scenario uses an immutable saved assumption set.",
    )
    if st.button(
        "Run pricing indication", type="primary", icon=":material/calculate:", disabled=not chosen
    ):
        st.session_state.pricing_runs = [run_pricing(study, by_label[c]) for c in chosen]

    runs = st.session_state.get("pricing_runs") or []
    if not runs:
        st.stop()
    st.warning(
        "Preliminary indication only — not a filed tariff, quote or binding premium. Excludes "
        "taxes, reinsurance, investment income, capital cost, large-claim pooling and IBNR.",
        icon=":material/gavel:",
    )
    if len(runs) > 1:
        st.subheader("Scenario comparison — indicated rate PMPM (IDR)")
        cmp = compare_scenarios(runs)
        fmt = {c: ("{:+.1%}" if " vs " in c else "{:,.0f}") for c in cmp.columns if c != "segment"}
        st.dataframe(cmp.style.format(fmt, na_rep="N/A"), hide_index=True)

    for run in runs:
        a = run.assumptions
        with st.container(border=True):
            st.subheader(a.label)
            st.caption(
                f"Owner {a.owner} · created {a.created_at:%Y-%m-%d %H:%M} UTC · trend "
                f"{a.annual_trend:.2%} over {a.elapsed_months:g} months"
                f"{' (illustrative)' if a.trend_is_illustrative else ''} · fixed "
                f"{a.fixed_expense_pmpm:,.0f} IDR PMPM · v {a.variable_expense_pct:.1%} · c "
                f"{a.commission_pct:.1%} · m {a.target_margin_pct:.1%} · d = "
                f"{a.loading_denominator:.4f} · {a.weighting_method}"
            )
            res = run.results
            n_blocked = int((res["status"] == BLOCKED).sum())
            if n_blocked:
                st.error(
                    f"{n_blocked} segment(s) blocked — see blocked_reason.", icon=":material/block:"
                )
            fmt = {
                "member_months": "{:,.0f}",
                "claim_count": "{:,.0f}",
                "weighted_pure_premium": "{:,.0f}",
                "trend_factor": "{:.4f}",
                "projected_pure_premium": "{:,.0f}",
                "fixed_expense_pmpm": "{:,.0f}",
                "loading_denominator": "{:.4f}",
                "indicated_rate_pmpm": "{:,.0f}",
                "current_rate_pmpm": "{:,.0f}",
                "indicated_change": "{:+.1%}",
            }
            st.dataframe(res.style.format(fmt, na_rep="N/A"), hide_index=True)
            with st.expander("Formula trace"):
                st.markdown(
                    "PPₜ = claimsₜ ÷ member-monthsₜ → weighted PP = Σ wₜ·PPₜ (or ΣC ÷ ΣE) → "
                    "projected PP = weighted PP × (1+g)^(m/12) → indicated rate = (projected PP "
                    "+ fixed expense) ÷ (1 − v − c − m) → change = indicated ÷ current − 1"
                )
                seg = st.selectbox("Segment", res["segment"], key=f"trace_{a.label}")
                st.dataframe(
                    run.trace[run.trace["segment"] == seg].style.format(
                        {
                            "member_months": "{:,.0f}",
                            "claim_amount": "{:,.0f}",
                            "pure_premium": "{:,.0f}",
                            "weight": "{:.4f}",
                        },
                        na_rep="N/A",
                    ),
                    hide_index=True,
                )
                trace_row = (
                    res.set_index("segment").loc[[seg]].T.astype(str)
                )  # mixed types: display as text
                st.dataframe(trace_row, width="content")
