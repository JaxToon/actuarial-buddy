"""Canonical field definitions for exposure and claims inputs (see docs/PRD.md §7)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

FieldKind = Literal["str", "date", "number"]


@dataclass(frozen=True)
class FieldSpec:
    name: str
    kind: FieldKind
    required: bool
    description: str


EXPOSURE_FIELDS: tuple[FieldSpec, ...] = (
    FieldSpec("exposure_id", "str", True, "Unique exposure record ID"),
    FieldSpec("member_ref", "str", True, "Pseudonymous member reference (never a real ID)"),
    FieldSpec("group_ref", "str", True, "Employer/group identifier"),
    FieldSpec("plan_code", "str", True, "Product/benefit plan"),
    FieldSpec("coverage_start", "date", True, "Coverage start date"),
    FieldSpec("coverage_end", "date", True, "Coverage end date"),
    FieldSpec("earned_member_months", "number", True, "Earned exposure in member-months"),
    FieldSpec("age_band", "str", False, "Pre-banded age category"),
    FieldSpec("region", "str", False, "Coarse geographic category"),
    FieldSpec("earned_premium", "number", False, "Earned premium for the exposure period"),
    FieldSpec("current_rate_pmpm", "number", False, "Current price per member-month"),
    FieldSpec("currency", "str", False, "ISO currency code"),
)

CLAIM_FIELDS: tuple[FieldSpec, ...] = (
    FieldSpec("claim_id", "str", True, "Unique claim identifier at the declared grain"),
    FieldSpec("exposure_id", "str", True, "Link to exposure record"),
    FieldSpec("service_date", "date", True, "Date the service/risk event occurred"),
    FieldSpec("paid_amount", "number", True, "Paid amount"),
    FieldSpec("reported_date", "date", False, "Date reported"),
    FieldSpec("case_reserve", "number", False, "Outstanding case reserve"),
    FieldSpec("incurred_amount", "number", False, "Supplied incurred amount"),
    FieldSpec("claim_type", "str", False, "Broad category, e.g. inpatient/outpatient"),
    FieldSpec("currency", "str", False, "ISO currency code"),
)


def required_names(fields: tuple[FieldSpec, ...]) -> list[str]:
    return [f.name for f in fields if f.required]


def all_names(fields: tuple[FieldSpec, ...]) -> list[str]:
    return [f.name for f in fields]
