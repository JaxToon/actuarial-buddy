"""Date helpers."""

from __future__ import annotations

from datetime import date


def months_between(start: date, end: date) -> float:
    """Elapsed months using a 365.25/12-day month. Negative if end < start."""
    return (end - start).days / (365.25 / 12)
