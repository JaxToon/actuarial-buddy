"""Write the synthetic demo dataset, invalid fixture and blank templates to data/synthetic/.

Usage: python scripts/generate_synthetic_data.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd  # noqa: E402

from actuarybench.config import SYNTHETIC_DIR  # noqa: E402
from actuarybench.synthetic import (  # noqa: E402
    CLAIMS_COLUMNS,
    EXPOSURE_COLUMNS,
    generate_invalid_fixture,
    generate_synthetic_dataset,
)


def main() -> None:
    SYNTHETIC_DIR.mkdir(parents=True, exist_ok=True)
    ds = generate_synthetic_dataset()
    ds.exposures.to_csv(SYNTHETIC_DIR / "demo_exposures.csv", index=False, date_format="%Y-%m-%d")
    ds.claims.to_csv(SYNTHETIC_DIR / "demo_claims.csv", index=False, date_format="%Y-%m-%d")
    bad = generate_invalid_fixture()
    bad.exposures.to_csv(SYNTHETIC_DIR / "invalid_exposures.csv", index=False)
    bad.claims.to_csv(SYNTHETIC_DIR / "invalid_claims.csv", index=False)
    with pd.ExcelWriter(SYNTHETIC_DIR / "template.xlsx", engine="xlsxwriter") as xw:
        pd.DataFrame(columns=EXPOSURE_COLUMNS).to_excel(xw, sheet_name="exposures", index=False)
        pd.DataFrame(columns=CLAIMS_COLUMNS).to_excel(xw, sheet_name="claims", index=False)
    print(f"exposures={len(ds.exposures)} claims={len(ds.claims)} -> {SYNTHETIC_DIR}")


if __name__ == "__main__":
    main()
