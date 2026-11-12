"""Deterministic synthetic group-health exposure and claims generator.

All records produced here are SYNTHETIC. They do not represent any real insurer,
employer, member or claim. Member references are random tokens; no names, national IDs,
dates of birth, diagnoses or addresses are generated.

The clean demo dataset is internally consistent. Data-quality edge cases are produced
only by :func:`generate_invalid_fixture`, never mixed into the clean dataset.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import pandas as pd

from actuarybench.config import DEFAULT_CURRENCY, DEFAULT_SEED

EXPOSURE_COLUMNS = [
    "exposure_id",
    "member_ref",
    "group_ref",
    "plan_code",
    "coverage_start",
    "coverage_end",
    "earned_member_months",
    "age_band",
    "region",
    "earned_premium",
    "current_rate_pmpm",
    "currency",
]
CLAIMS_COLUMNS = [
    "claim_id",
    "exposure_id",
    "service_date",
    "reported_date",
    "paid_amount",
    "case_reserve",
    "incurred_amount",
    "claim_type",
    "currency",
]

# plan_code: (base current_rate_pmpm IDR, annual claim frequency per member, base severity IDR)
PLANS = {
    "PLAN_A": (95_000, 2.4, 420_000),
    "PLAN_B": (150_000, 2.8, 560_000),
    "PLAN_C": (240_000, 3.1, 780_000),
}
AGE_BANDS = {"18-29": 0.8, "30-39": 1.0, "40-49": 1.2, "50-64": 1.6}
REGIONS = ["JAVA", "SUMATRA", "KALIMANTAN", "SULAWESI", "EAST"]
CLAIM_TYPES = ["OUTPATIENT", "INPATIENT", "DENTAL"]
CLAIM_TYPE_PROBS = [0.82, 0.10, 0.08]
CLAIM_TYPE_SEVERITY_MULT = {"OUTPATIENT": 0.45, "INPATIENT": 6.5, "DENTAL": 0.7}


@dataclass(frozen=True)
class SyntheticDataset:
    exposures: pd.DataFrame
    claims: pd.DataFrame


def _month_end(year: int, month: int) -> date:
    return (date(year, month, 1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)


def generate_synthetic_dataset(
    seed: int = DEFAULT_SEED,
    n_groups: int = 12,
    years: tuple[int, ...] = (2023, 2024, 2025),
    evaluation_date: date = date(2026, 3, 31),
) -> SyntheticDataset:
    """Generate a reproducible clean synthetic dataset.

    Exposure grain: one row per member per policy year (calendar-year coverage, with
    some mid-year joins/terminations producing partial member-months).
    Claims grain: one row per claim (no claim lines). ``incurred_amount = paid + case_reserve``.
    Claims reported after ``evaluation_date`` are omitted, so recent periods are
    deliberately less developed (realistic paid-claims lag).
    """
    rng = np.random.default_rng(seed)
    exp_rows: list[dict] = []
    clm_rows: list[dict] = []
    member_counter = 0
    claim_counter = 0
    plan_codes = list(PLANS)
    age_bands = list(AGE_BANDS)

    for g in range(1, n_groups + 1):
        group_ref = f"GRP{g:03d}"
        plan_code = plan_codes[g % len(plan_codes)]
        region = REGIONS[int(rng.integers(len(REGIONS)))]
        members = []
        for _ in range(int(rng.integers(40, 160))):
            member_counter += 1
            members.append((f"M{member_counter:06d}", age_bands[int(rng.integers(len(age_bands)))]))
        rate, freq, sev = PLANS[plan_code]
        for year in years:
            k = year - years[0]
            rate_y = round(rate * (1.07**k))
            for member_ref, age_band in members:
                start_m = 1 if rng.random() > 0.12 else int(rng.integers(2, 12))
                end_m = 12 if rng.random() > 0.08 else int(rng.integers(start_m, 13))
                start = date(year, start_m, 1)
                end = _month_end(year, end_m)
                mm = float(end_m - start_m + 1)
                exposure_id = f"EXP{year}{member_ref[1:]}"
                exp_rows.append(
                    {
                        "exposure_id": exposure_id,
                        "member_ref": member_ref,
                        "group_ref": group_ref,
                        "plan_code": plan_code,
                        "coverage_start": start,
                        "coverage_end": end,
                        "earned_member_months": mm,
                        "age_band": age_band,
                        "region": region,
                        "earned_premium": float(rate_y * mm),
                        "current_rate_pmpm": float(rate_y),
                        "currency": DEFAULT_CURRENCY,
                    }
                )
                lam = freq * AGE_BANDS[age_band] * (1.06**k) * mm / 12
                for _ in range(int(rng.poisson(lam))):
                    service = start + timedelta(days=int(rng.integers(0, (end - start).days + 1)))
                    reported = service + timedelta(days=int(rng.gamma(2.0, 15.0)))
                    if reported > evaluation_date:
                        continue
                    ctype = str(rng.choice(CLAIM_TYPES, p=CLAIM_TYPE_PROBS))
                    mean = sev * CLAIM_TYPE_SEVERITY_MULT[ctype] * (1.08**k)
                    amount = float(round(rng.lognormal(np.log(mean) - 0.5, 1.0), -2))
                    age_days = (evaluation_date - reported).days
                    open_share = 0.0 if age_days > 120 else float(rng.uniform(0.2, 1.0))
                    reserve = float(round(amount * open_share, -2))
                    claim_counter += 1
                    clm_rows.append(
                        {
                            "claim_id": f"CLM{claim_counter:07d}",
                            "exposure_id": exposure_id,
                            "service_date": service,
                            "reported_date": reported,
                            "paid_amount": amount - reserve,
                            "case_reserve": reserve,
                            "incurred_amount": amount,
                            "claim_type": ctype,
                            "currency": DEFAULT_CURRENCY,
                        }
                    )

    exposures = pd.DataFrame(exp_rows, columns=EXPOSURE_COLUMNS)
    claims = pd.DataFrame(clm_rows, columns=CLAIMS_COLUMNS)
    for col in ("coverage_start", "coverage_end"):
        exposures[col] = pd.to_datetime(exposures[col])
    for col in ("service_date", "reported_date"):
        claims[col] = pd.to_datetime(claims[col])
    return SyntheticDataset(exposures=exposures, claims=claims)


def generate_invalid_fixture() -> SyntheticDataset:
    """Small hand-built SYNTHETIC dataset with deliberate data-quality defects.

    Each row documents its defect in the ``_defect`` note column. Values are raw strings /
    numbers as a user file would contain them (dates are not pre-parsed).
    """
    s, e, prem, rate = "2025-01-01", "2025-12-31", 1_140_000, 95_000
    # fmt: off
    exp_rows = [
        ["EXP1", "M1", "GRP1", "PLAN_A", s, e, 12, "30-39", "JAVA", prem, rate, "IDR", "valid"],
        ["EXP2", "M2", "GRP1", "PLAN_A", s, e, 12, "40-49", "JAVA", prem, rate, "IDR", "valid"],
        ["EXP3", "M3", "GRP1", "PLAN_A", "2025-06-01", "2025-03-31", 4, "40-49", "JAVA",
         380_000, rate, "IDR", "coverage_end before coverage_start"],
        ["EXP4", "M4", "GRP1", None, s, e, 12, "18-29", "JAVA", prem, rate, "IDR",
         "missing plan_code"],
        ["EXP5", "M5", "GRP1", "PLAN_A", s, e, -3, "18-29", "JAVA", prem, rate, "IDR",
         "negative earned_member_months"],
        ["EXP6", "M6", "GRP1", "PLAN_A", s, e, 12, "30-39", "JAVA", prem, rate, "IDR",
         "duplicate exposure_id"],
        ["EXP6", "M8", "GRP1", "PLAN_A", s, e, 12, "30-39", "JAVA", prem, rate, "IDR",
         "duplicate exposure_id"],
        ["EXP7", "M7", "GRP1", "PLAN_A", "not-a-date", e, 12, "30-39", "JAVA", prem, rate,
         "IDR", "unparseable coverage_start"],
    ]
    clm_rows = [
        ["C1", "EXP1", "2025-03-10", "2025-03-20", 500_000, 0, 500_000, "OUTPATIENT", "IDR",
         "valid"],
        ["C2", "EXP1", "2025-05-02", "2025-05-15", 300_000, 100_000, 400_000, "OUTPATIENT",
         "IDR", "duplicate claim_id"],
        ["C2", "EXP2", "2025-06-01", "2025-06-09", 200_000, 0, 200_000, "DENTAL", "IDR",
         "duplicate claim_id"],
        ["C3", "EXP2", "2025-06-11", "2025-06-20", 120_000, 30_000, 150_000, "OUTPATIENT",
         "IDR", "valid"],
        ["C4", "EXP999", "2025-04-01", "2025-04-10", 250_000, 0, 250_000, "OUTPATIENT", "IDR",
         "orphan claim (no exposure)"],
        ["C5", "EXP2", "2024-11-30", "2024-12-05", 150_000, 0, 150_000, "OUTPATIENT", "IDR",
         "service_date outside coverage"],
        ["C6", "EXP2", "2025-07-07", "2025-07-10", -90_000, 0, -90_000, "OUTPATIENT", "IDR",
         "negative paid_amount"],
        ["C7", "EXP2", "2025-08-01", "2025-08-05", 100_000, 50_000, 999_000, "OUTPATIENT",
         "IDR", "incurred != paid + case_reserve"],
        ["C8", "EXP2", None, "2025-08-05", 100_000, 0, 100_000, "OUTPATIENT", "IDR",
         "missing service_date"],
        ["C9", "EXP5", "2025-02-01", "2025-02-05", 100_000, 0, 100_000, "OUTPATIENT", "IDR",
         "linked exposure excluded"],
    ]
    # fmt: on
    return SyntheticDataset(
        exposures=pd.DataFrame(exp_rows, columns=[*EXPOSURE_COLUMNS, "_defect"]),
        claims=pd.DataFrame(clm_rows, columns=[*CLAIMS_COLUMNS, "_defect"]),
    )
