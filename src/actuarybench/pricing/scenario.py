"""Apply an assumption set to an experience study, segment by segment, with a full trace.

A segment whose calculation is blocked (no exposure in a weighted period, zero exposure,
invalid loads) gets status ``BLOCKED`` with the reason; it is never filled with a fallback.
Current rate for the indicated change (decision D12, M4.2): the member-month-weighted current
rate of the **latest study experience period**, used only when every member-month of that
period in the segment supplied a positive rate. Otherwise the comparison is BLOCKED
(``change_status``) with the missing input named. There is no fallback to an earlier period or
to a partial average. The indicated rate itself does not depend on the current rate and is
still produced. The D12 interpretation remains open for practitioner/actuarial review.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from actuarybench.pricing.indication import PricingError, calculate_indicated_rate
from actuarybench.pricing.trend import TrendError, project_claim_cost
from actuarybench.schemas.assumptions import AssumptionSet
from actuarybench.studies.segmentation import ExperienceStudyResult
from actuarybench.studies.weighting import WeightingError, calculate_weighted_pure_premium

ALL_SEGMENTS = "ALL"
OK = "OK"
BLOCKED = "BLOCKED"
CURRENT_RATE_BASIS = "latest_experience_period_full_coverage"
_FULL = 1.0 - 1e-12


@dataclass(frozen=True)
class PricingRun:
    assumptions: AssumptionSet
    study: ExperienceStudyResult
    results: pd.DataFrame  # one row per segment (+ overall row "ALL")
    trace: pd.DataFrame  # per segment × period: member months, claims, PP, weight
    current_rate_basis: str = CURRENT_RATE_BASIS


def _current_rate(periods: pd.DataFrame, latest_period: int) -> tuple[float | None, str]:
    """Return (rate, "") or (None, reason). Never substitutes another period's rate."""
    row = periods[periods["experience_period"] == latest_period]
    if row.empty or not float(row["earned_member_months"].iloc[0]) > 0:
        return None, f"no exposure in latest experience period {latest_period}"
    cov = row["current_rate_coverage"].iloc[0] if "current_rate_coverage" in row else None
    if cov is None or pd.isna(cov) or cov <= 0:
        return None, (
            f"current_rate_pmpm not supplied for latest experience period {latest_period}"
        )
    if cov < _FULL:
        return None, (
            f"current_rate_pmpm missing for {1 - cov:.1%} of member-months in latest "
            f"experience period {latest_period}"
        )
    return float(row["current_rate_pmpm"].iloc[0]), ""


def _segment_label(keys: tuple, dims: tuple[str, ...]) -> str:
    if not dims:
        return ALL_SEGMENTS
    return " | ".join(
        f"{d}={'(blank)' if pd.isna(k) else k}" for d, k in zip(dims, keys, strict=True)
    )


def _price_one(
    label: str,
    keys: dict,
    periods: pd.DataFrame,
    all_periods: list[int],
    seg_row: pd.Series,
    a: AssumptionSet,
    study: ExperienceStudyResult,
) -> tuple[dict, pd.DataFrame]:
    full = (
        pd.DataFrame({"experience_period": all_periods})
        .merge(periods, on="experience_period", how="left")
        .fillna({"earned_member_months": 0.0, "claim_amount": 0.0, "claim_count": 0})
    )
    warnings: list[str] = []
    if bool(seg_row.get("low_exposure", False)):
        warnings.append("LOW EXPOSURE — REVIEW")
    if pd.isna(seg_row.get("earned_premium")):
        warnings.append("Missing/incomplete premium")
    if study.config.claim_basis == "paid":
        warnings.append("Paid-only claims")
    if a.trend_is_illustrative:
        warnings.append("Illustrative trend assumption")
    n_with_exposure = int((full["earned_member_months"] > 0).sum())
    if n_with_exposure < 2:
        warnings.append(f"Only {n_with_exposure} experience period(s) with exposure")

    row: dict = {
        **keys,
        "segment": label,
        "status": OK,
        "blocked_reason": "",
        "member_months": float(full["earned_member_months"].sum()),
        "claim_count": int(full["claim_count"].sum()),
    }
    trace = full.assign(segment=label)
    try:
        w = calculate_weighted_pure_premium(full, a.weighting_method, a.period_weights)
        trace = w.periods.assign(segment=label)
        tp = project_claim_cost(w.weighted_pure_premium, a.annual_trend, a.elapsed_months)
        current, change_reason = _current_rate(periods, max(all_periods))
        pr = calculate_indicated_rate(
            tp.projected_pure_premium,
            a.fixed_expense_pmpm,
            a.variable_expense_pct,
            a.commission_pct,
            a.target_margin_pct,
            current,
        )
        if current is None:
            row |= {"change_status": BLOCKED, "change_blocked_reason": change_reason}
        else:
            row |= {"change_status": OK, "change_blocked_reason": ""}
        row |= {
            "weighted_pure_premium": w.weighted_pure_premium,
            "trend_factor": tp.trend_factor,
            "projected_pure_premium": tp.projected_pure_premium,
            "fixed_expense_pmpm": pr.fixed_expense_pmpm,
            "loading_denominator": pr.loading_denominator,
            "indicated_rate_pmpm": pr.indicated_rate_pmpm,
            "current_rate_pmpm": pr.current_rate_pmpm,
            "indicated_change": pr.indicated_change,
        }
    except (WeightingError, TrendError, PricingError) as exc:
        row |= {
            "status": BLOCKED,
            "blocked_reason": str(exc),
            "change_status": BLOCKED,
            "change_blocked_reason": "indicated rate blocked",
        }
    row["warnings"] = "; ".join(warnings)
    return row, trace


def run_pricing(study: ExperienceStudyResult, assumptions: AssumptionSet) -> PricingRun:
    dims = study.config.segment_by
    all_periods = sorted(int(p) for p in study.by_period["experience_period"])
    rows: list[dict] = []
    traces: list[pd.DataFrame] = []

    row, tr = _price_one(
        ALL_SEGMENTS, {}, study.by_period, all_periods, study.overall.iloc[0], assumptions, study
    )
    rows.append(row)
    traces.append(tr)
    if dims:
        seg_index = study.by_segment.set_index(list(dims))
        for keys, grp in study.by_period_segment.groupby(list(dims), dropna=False, sort=True):
            keys = keys if isinstance(keys, tuple) else (keys,)
            seg_row = seg_index.loc[keys if len(keys) > 1 else keys[0]]
            if isinstance(seg_row, pd.DataFrame):
                seg_row = seg_row.iloc[0]
            label = _segment_label(keys, dims)
            row, tr = _price_one(
                label,
                dict(zip(dims, keys, strict=True)),
                grp,
                all_periods,
                seg_row,
                assumptions,
                study,
            )
            rows.append(row)
            traces.append(tr)

    cols = [
        "segment",
        *dims,
        "status",
        "blocked_reason",
        "member_months",
        "claim_count",
        "weighted_pure_premium",
        "trend_factor",
        "projected_pure_premium",
        "fixed_expense_pmpm",
        "loading_denominator",
        "indicated_rate_pmpm",
        "current_rate_pmpm",
        "indicated_change",
        "change_status",
        "change_blocked_reason",
        "warnings",
    ]
    results = pd.DataFrame(rows).reindex(columns=cols)
    trace_cols = [
        "segment",
        "experience_period",
        "member_months",
        "claim_amount",
        "pure_premium",
        "weight",
    ]
    trace = pd.concat(traces, ignore_index=True).reindex(columns=trace_cols)
    return PricingRun(assumptions, study, results, trace)


def compare_scenarios(runs: list[PricingRun]) -> pd.DataFrame:
    """Wide table of indicated rate PMPM per segment, one column per assumption set."""
    if not runs:
        return pd.DataFrame()
    out = None
    for r in runs:
        col = r.results.set_index("segment")["indicated_rate_pmpm"].rename(r.assumptions.label)
        out = col.to_frame() if out is None else out.join(col, how="outer")
    base = runs[0].assumptions.label
    for r in runs[1:]:
        lbl = r.assumptions.label
        out[f"{lbl} vs {base}"] = out[lbl] / out[base] - 1
    return out.reset_index()
