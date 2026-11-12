"""Experience study over validated exposure and claims data.

Study-period rules (documented method choices — see docs/METHOD_DECISIONS.md):
- An exposure record is included only if its whole coverage period lies inside the study
  period. Records that only partly overlap are excluded and counted; exposure is never
  pro-rated, because no apportionment method is specified in ACTUARIAL_METHODS.md.
- A claim is included if its exposure record is included, its service date lies in the
  study period, and (when ``reported_date`` is supplied) it was reported on or before the
  evaluation date.
- Experience period = calendar year of ``coverage_start`` ("policy year by start year").
- Low-exposure flag: member-months below a user threshold. A review flag, not credibility.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Literal

import pandas as pd

from actuarybench.studies.metrics import METRIC_COLUMNS, add_metric_columns

ClaimBasis = Literal["incurred", "paid"]
LOW_EXPOSURE_LABEL = "LOW EXPOSURE — REVIEW"
SEGMENT_CANDIDATES = ("plan_code", "age_band", "region", "group_ref")


class StudyConfigError(ValueError):
    """Invalid study configuration."""


@dataclass(frozen=True)
class StudyConfig:
    period_start: date
    period_end: date
    evaluation_date: date
    claim_basis: ClaimBasis = "incurred"
    segment_by: tuple[str, ...] = ("plan_code",)
    low_exposure_threshold_mm: float = 600.0

    def validate(self) -> None:
        if self.period_end < self.period_start:
            raise StudyConfigError("Study period end is before start.")
        if self.evaluation_date < self.period_start:
            raise StudyConfigError("Evaluation date is before the study period start.")
        if self.claim_basis not in ("incurred", "paid"):
            raise StudyConfigError(f"Unknown claim basis {self.claim_basis!r}.")
        if self.low_exposure_threshold_mm < 0:
            raise StudyConfigError("Low-exposure threshold must be non-negative.")
        if len(set(self.segment_by)) != len(self.segment_by):
            raise StudyConfigError("Segment dimensions must be distinct.")

    @property
    def claim_basis_label(self) -> str:
        if self.claim_basis == "paid":
            return "Paid claims as of evaluation date (paid-claims experience; no IBNR)"
        return "Incurred claims = paid + case reserve (reported claims only; no IBNR)"


@dataclass(frozen=True)
class ExperienceStudyResult:
    config: StudyConfig
    overall: pd.DataFrame
    by_segment: pd.DataFrame
    by_period: pd.DataFrame
    by_period_segment: pd.DataFrame
    exclusions: pd.DataFrame
    warnings: tuple[str, ...] = field(default_factory=tuple)
    exposure_rows_used: int = 0
    claim_rows_used: int = 0


def _ts(d: date) -> pd.Timestamp:
    return pd.Timestamp(d)


def _aggregate(
    exp: pd.DataFrame, clm: pd.DataFrame, keys: list[str], cfg: StudyConfig
) -> pd.DataFrame:
    if keys:
        e = exp.groupby(keys, dropna=False).agg(
            earned_member_months=("earned_member_months", "sum"),
            earned_premium=("earned_premium", lambda s: s.sum(min_count=len(s))),
            current_rate_pmpm_weighted=("_rate_x_mm", "sum"),
            rate_mm=("_rate_mm", "sum"),
        )
        c = clm.groupby(keys, dropna=False).agg(
            claim_count=("claim_id", "nunique"), claim_amount=("_amount", "sum")
        )
        t = e.join(c, how="left").reset_index()
    else:
        t = pd.DataFrame(
            [
                {
                    "earned_member_months": exp["earned_member_months"].sum(),
                    "earned_premium": exp["earned_premium"].sum(min_count=len(exp)),
                    "current_rate_pmpm_weighted": exp["_rate_x_mm"].sum(),
                    "rate_mm": exp["_rate_mm"].sum(),
                    "claim_count": clm["claim_id"].nunique(),
                    "claim_amount": clm["_amount"].sum(),
                }
            ]
        )
    t["claim_count"] = t["claim_count"].fillna(0).astype(int)
    t["claim_amount"] = t["claim_amount"].fillna(0.0)
    # Member-month-weighted current rate, only over records that supplied a rate.
    t["current_rate_pmpm"] = t["current_rate_pmpm_weighted"] / t["rate_mm"].where(t["rate_mm"] > 0)
    t = add_metric_columns(t)
    t["low_exposure"] = t["earned_member_months"] < cfg.low_exposure_threshold_mm
    t["flag"] = t["low_exposure"].map({True: LOW_EXPOSURE_LABEL, False: ""})
    return t[[*keys, *METRIC_COLUMNS, "current_rate_pmpm", "low_exposure", "flag"]]


def run_experience_study(
    exposures: pd.DataFrame, claims: pd.DataFrame, config: StudyConfig
) -> ExperienceStudyResult:
    """Run the experience study on *validated* (clean) exposure and claims tables."""
    config.validate()
    missing_dims = [d for d in config.segment_by if d not in exposures.columns]
    if missing_dims:
        raise StudyConfigError(f"Segment dimension(s) not in exposure data: {missing_dims}")
    if config.claim_basis == "incurred" and "incurred_amount" not in claims.columns:
        raise StudyConfigError(
            "Incurred basis selected but no incurred_amount or case_reserve was supplied. "
            "Choose the paid basis."
        )

    p0, p1, ev = _ts(config.period_start), _ts(config.period_end), _ts(config.evaluation_date)
    exclusions: list[dict] = []
    warnings: list[str] = []

    exp = exposures.copy()
    inside = (exp["coverage_start"] >= p0) & (exp["coverage_end"] <= p1)
    overlap = ~inside & (exp["coverage_start"] <= p1) & (exp["coverage_end"] >= p0)
    exclusions.append(
        {
            "record_type": "exposure",
            "reason": "partially_outside_study_period",
            "rows": int(overlap.sum()),
            "member_months": float(exp.loc[overlap, "earned_member_months"].sum()),
        }
    )
    exclusions.append(
        {
            "record_type": "exposure",
            "reason": "outside_study_period",
            "rows": int((~inside & ~overlap).sum()),
            "member_months": float(exp.loc[~inside & ~overlap, "earned_member_months"].sum()),
        }
    )
    exp = exp[inside].copy()
    exp["experience_period"] = exp["coverage_start"].dt.year.astype(int)
    if "earned_premium" not in exp:
        exp["earned_premium"] = float("nan")
    rate = (
        exp["current_rate_pmpm"]
        if "current_rate_pmpm" in exp
        else pd.Series(float("nan"), index=exp.index)
    )
    has_rate = rate.notna() & (rate > 0)
    exp["_rate_x_mm"] = (rate * exp["earned_member_months"]).where(has_rate, 0.0)
    exp["_rate_mm"] = exp["earned_member_months"].where(has_rate, 0.0)
    for d in config.segment_by:
        n_missing = int(exp[d].isna().sum())
        if n_missing:
            warnings.append(f"{n_missing:,} exposure rows have no {d}; shown as a blank segment.")

    clm = claims.copy()
    amount_col = "incurred_amount" if config.claim_basis == "incurred" else "paid_amount"
    linked = clm["exposure_id"].isin(exp["exposure_id"])
    exclusions.append(
        {
            "record_type": "claims",
            "reason": "exposure_not_in_study",
            "rows": int((~linked).sum()),
            "amount": float(clm.loc[~linked, amount_col].sum()),
        }
    )
    clm = clm[linked]
    in_period = (clm["service_date"] >= p0) & (clm["service_date"] <= p1)
    exclusions.append(
        {
            "record_type": "claims",
            "reason": "service_date_outside_study_period",
            "rows": int((~in_period).sum()),
            "amount": float(clm.loc[~in_period, amount_col].sum()),
        }
    )
    clm = clm[in_period]
    if "reported_date" in clm and clm["reported_date"].notna().any():
        late = clm["reported_date"] > ev
        exclusions.append(
            {
                "record_type": "claims",
                "reason": "reported_after_evaluation_date",
                "rows": int(late.sum()),
                "amount": float(clm.loc[late, amount_col].sum()),
            }
        )
        clm = clm[~late]
        if clm["reported_date"].isna().any():
            warnings.append(
                "Some claims have no reported_date; they are included regardless "
                "of the evaluation date."
            )
    else:
        warnings.append(
            "No reported_date supplied; the evaluation date cannot be applied to claims."
        )

    cols = ["exposure_id", "experience_period", *config.segment_by]
    clm = clm.merge(exp[cols], on="exposure_id", how="left")
    clm["_amount"] = clm[amount_col].astype(float)
    nan_amount = int(clm["_amount"].isna().sum())
    if nan_amount:
        raise StudyConfigError(f"{nan_amount} included claims have no {amount_col}.")

    if config.claim_basis == "paid":
        warnings.append(
            "Paid-claims experience: excludes case reserves and unreported claims "
            "(IBNR). Recent periods are understated."
        )
    else:
        warnings.append(
            "Incurred = paid + case reserves on reported claims. No allowance for "
            "IBNR or claim development is made."
        )
    if exp["earned_premium"].isna().any():
        warnings.append(
            "Earned premium is missing for some exposure; loss ratios for affected "
            "segments show N/A."
        )
    last_period_end = p1
    if (ev - last_period_end).days < 90:
        warnings.append(
            "Evaluation date is less than 3 months after the study period end; "
            "the latest period may be materially incomplete."
        )

    seg = list(config.segment_by)
    by_segment = _aggregate(exp, clm, seg, config)
    n_low = int(by_segment["low_exposure"].sum())
    if n_low:
        warnings.append(
            f"{n_low} segment(s) below {config.low_exposure_threshold_mm:,.0f} "
            "member-months flagged LOW EXPOSURE — REVIEW."
        )
    return ExperienceStudyResult(
        config=config,
        overall=_aggregate(exp, clm, [], config),
        by_segment=by_segment,
        by_period=_aggregate(exp, clm, ["experience_period"], config),
        by_period_segment=_aggregate(exp, clm, ["experience_period", *seg], config),
        exclusions=pd.DataFrame(exclusions).fillna(0.0),
        warnings=tuple(warnings),
        exposure_rows_used=len(exp),
        claim_rows_used=len(clm),
    )
