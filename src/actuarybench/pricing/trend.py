"""Simple trend projection (docs/ACTUARIAL_METHODS.md §5).

Trend factor     = (1 + g) ** (m / 12)
Projected PP     = Weighted PP × trend factor

g is a user-supplied annual trend; m is user-supplied elapsed months. The tool never
estimates trend from data.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date

from actuarybench.utils.dates import months_between


class TrendError(ValueError):
    pass


@dataclass(frozen=True)
class TrendProjection:
    base_pure_premium: float
    annual_trend: float
    elapsed_months: float
    trend_factor: float
    projected_pure_premium: float


def project_claim_cost(
    pure_premium: float, annual_trend: float, elapsed_months: float
) -> TrendProjection:
    if not math.isfinite(pure_premium) or pure_premium < 0:
        raise TrendError("Pure premium must be a finite, non-negative number.")
    if annual_trend <= -1:
        raise TrendError("Annual trend must be greater than -100%.")
    if elapsed_months < 0:
        raise TrendError("Elapsed months must be non-negative.")
    factor = (1.0 + annual_trend) ** (elapsed_months / 12.0)
    return TrendProjection(
        pure_premium, annual_trend, elapsed_months, factor, pure_premium * factor
    )


def midpoint(start: date, end: date) -> date:
    return start + (end - start) / 2


def suggest_elapsed_months(
    experience_start: date, experience_end: date, projection_start: date, projection_end: date
) -> float:
    """Months from experience-period midpoint to projection-period midpoint (a suggestion the
    user must confirm; 365.25/12-day months)."""
    return months_between(
        midpoint(experience_start, experience_end), midpoint(projection_start, projection_end)
    )
