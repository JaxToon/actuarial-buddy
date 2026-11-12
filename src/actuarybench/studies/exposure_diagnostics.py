"""DIAGNOSTIC ONLY — compare exposure conventions for a study period (decision D6).

Nothing in this module is used by the experience study, pricing, reports or saved runs.
It exists so that an actuary and practitioners can see how the unapproved choice of
partial-exposure convention would move the results. None of the candidates is an approved
methodology.

Conventions compared (coverage and study end dates are inclusive):

- ``whole_record`` — the pre-M4.2 production rule: only records wholly inside the period;
  partly-overlapping records dropped (biased for non-aligned periods).
- ``overlap_days`` — candidate: effective_start = max(coverage_start, study_start),
  effective_end = min(coverage_end, study_end), overlap_days = max(0, end − start + 1);
  member-months and premium pro-rated by overlap_days / coverage_days; claims counted when the
  service date lies in [effective_start, effective_end].
"""

from __future__ import annotations

from datetime import date

import pandas as pd

DIAGNOSTIC_LABEL = "DIAGNOSTIC — not an approved exposure methodology (D6 pending actuary)"


def _metrics(e: float, n: int, c: float, p: float) -> dict:
    return {
        "member_months": e,
        "claim_count": n,
        "claim_amount": c,
        "frequency_per_1000_my": n / (e / 12) * 1000 if e > 0 else None,
        "average_severity": c / n if n > 0 else None,
        "claim_cost_pmpm": c / e if e > 0 else None,
        "loss_ratio": c / p if p > 0 else None,
    }


def boundary_records(exposures: pd.DataFrame, period_start: date, period_end: date) -> pd.DataFrame:
    """Per-record overlap detail for records that straddle a study-period boundary."""
    p0, p1 = pd.Timestamp(period_start), pd.Timestamp(period_end)
    e = exposures
    es = e["coverage_start"].where(e["coverage_start"] > p0, p0)
    ee = e["coverage_end"].where(e["coverage_end"] < p1, p1)
    overlap_days = ((ee - es).dt.days + 1).clip(lower=0)
    cov_days = (e["coverage_end"] - e["coverage_start"]).dt.days + 1
    straddle = (overlap_days > 0) & (overlap_days < cov_days)
    out = pd.DataFrame(
        {
            "exposure_id": e["exposure_id"],
            "coverage_start": e["coverage_start"],
            "coverage_end": e["coverage_end"],
            "coverage_days": cov_days,
            "overlap_days": overlap_days,
            "earned_member_months": e["earned_member_months"],
            "pro_rated_member_months": e["earned_member_months"] * overlap_days / cov_days,
        }
    )
    return out[straddle].reset_index(drop=True)


def compare_exposure_conventions(
    exposures: pd.DataFrame,
    claims: pd.DataFrame,
    period_start: date,
    period_end: date,
    claim_basis: str = "incurred",
) -> pd.DataFrame:
    """Overall metrics under each convention, from *validated* (clean, typed) tables."""
    p0, p1 = pd.Timestamp(period_start), pd.Timestamp(period_end)
    amount = "incurred_amount" if claim_basis == "incurred" else "paid_amount"
    e = exposures.copy()
    if "earned_premium" not in e:
        e["earned_premium"] = float("nan")
    es = e["coverage_start"].where(e["coverage_start"] > p0, p0)
    ee = e["coverage_end"].where(e["coverage_end"] < p1, p1)
    ov = ((ee - es).dt.days + 1).clip(lower=0)
    cov = (e["coverage_end"] - e["coverage_start"]).dt.days + 1
    share = ov / cov

    whole = e[(e["coverage_start"] >= p0) & (e["coverage_end"] <= p1)]
    cw = claims[
        claims["exposure_id"].isin(whole["exposure_id"]) & claims["service_date"].between(p0, p1)
    ]
    rows = [
        {
            "convention": "whole_record",
            "records_used": len(whole),
            **_metrics(
                float(whole["earned_member_months"].sum()),
                int(cw["claim_id"].nunique()),
                float(cw[amount].sum()),
                float(whole["earned_premium"].sum(min_count=len(whole))),
            ),
        }
    ]
    used = e[ov > 0].assign(_es=es[ov > 0], _ee=ee[ov > 0])
    co = claims.merge(used[["exposure_id", "_es", "_ee"]], on="exposure_id")
    co = co[(co["service_date"] >= co["_es"]) & (co["service_date"] <= co["_ee"])]
    rows.append(
        {
            "convention": "overlap_days (candidate)",
            "records_used": len(used),
            **_metrics(
                float((e["earned_member_months"] * share).sum()),
                int(co["claim_id"].nunique()),
                float(co[amount].sum()),
                float((e["earned_premium"] * share)[ov > 0].sum(min_count=int((ov > 0).sum()))),
            ),
        }
    )
    return pd.DataFrame(rows)
