"""Experience-period weighting (docs/ACTUARIAL_METHODS.md §4).

Year-weighted:      Weighted PP = Σ w_t · PP_t,  PP_t = C_t / E_t,  Σ w_t = 1, w_t ≥ 0
Exposure-weighted:  Aggregate PP = Σ C_t / Σ E_t

The two are separate method options and are never mixed. Weights are never silently
re-normalised: if a period with positive weight has no exposure, the result is blocked.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from actuarybench.schemas.assumptions import WEIGHT_TOLERANCE, WeightingMethod


class WeightingError(ValueError):
    """Weighted pure premium cannot be calculated for the supplied inputs."""


@dataclass(frozen=True)
class WeightedExperienceResult:
    method: WeightingMethod
    periods: pd.DataFrame  # experience_period, member_months, claim_amount, pure_premium, weight
    weighted_pure_premium: float


def calculate_weighted_pure_premium(
    periods: pd.DataFrame,
    method: WeightingMethod,
    weights: dict[int, float] | None = None,
) -> WeightedExperienceResult:
    """``periods`` needs columns experience_period, earned_member_months, claim_amount."""
    t = periods[["experience_period", "earned_member_months", "claim_amount"]].copy()
    t = t.rename(columns={"earned_member_months": "member_months"})
    t["experience_period"] = t["experience_period"].astype(int)
    if (t["member_months"] < 0).any() or (t["claim_amount"] < 0).any():
        raise WeightingError("Negative exposure or claim amount in period data.")
    mm = t["member_months"]
    t["pure_premium"] = (t["claim_amount"] / mm.where(mm > 0)).astype(float)

    if method == "exposure_weighted":
        total_e = float(mm.sum())
        if total_e <= 0:
            raise WeightingError("No exposure in any experience period.")
        t["weight"] = mm / total_e  # implied exposure weights, for display only
        return WeightedExperienceResult(method, t, float(t["claim_amount"].sum()) / total_e)

    if method != "year_weighted":
        raise WeightingError(f"Unknown weighting method {method!r}.")
    if not weights:
        raise WeightingError("Year-weighted method requires explicit period weights.")
    if any(w < 0 for w in weights.values()):
        raise WeightingError("Period weights must be non-negative.")
    if abs(sum(weights.values()) - 1.0) > WEIGHT_TOLERANCE:
        raise WeightingError(f"Period weights must sum to 1 (got {sum(weights.values()):.6f}).")
    weights = {int(k): float(v) for k, v in weights.items()}
    present = set(t["experience_period"])
    missing = sorted(p for p, w in weights.items() if w > 0 and p not in present)
    t["weight"] = t["experience_period"].map(weights).fillna(0.0)
    no_exposure = t.loc[(t["weight"] > 0) & t["pure_premium"].isna(), "experience_period"]
    blocked = sorted({*missing, *no_exposure.tolist()})
    if blocked:
        raise WeightingError(
            f"Period(s) {blocked} carry positive weight but have no exposure; "
            "adjust weights explicitly."
        )
    used = t[t["weight"] > 0]
    return WeightedExperienceResult(method, t, float((used["weight"] * used["pure_premium"]).sum()))
