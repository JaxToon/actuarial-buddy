"""Static project configuration (paths and limits). No hidden runtime state."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
SYNTHETIC_DIR = DATA_DIR / "synthetic"
UPLOADS_DIR = DATA_DIR / "uploads"
OUTPUTS_DIR = DATA_DIR / "outputs"
ARTIFACTS_DIR = DATA_DIR / "artifacts"  # local content-addressed run snapshots (gitignored)
DB_PATH = DATA_DIR / "actuarybench.db"

DEFAULT_SEED = 20261112
DEFAULT_CURRENCY = "IDR"
MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB
ALLOWED_UPLOAD_SUFFIXES = (".csv", ".xlsx")
DEFAULT_LOW_EXPOSURE_THRESHOLD_MM = 600.0  # member-months; review flag only
