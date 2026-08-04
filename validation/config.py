"""Shared paths and constants for the validation scripts.

The heavy validation dataset (cached daily ET0, Xavier reference, sensitivity
CSVs) lives in the ``EVAonline_validation`` package, which is *not*
tracked by git. These scripts read from it and write reproducible artefacts
into ``validation/outputs/`` (tracked).
"""

from __future__ import annotations

import os
from pathlib import Path

# Repository root = parent of this ``validation`` package.
REPO_ROOT = Path(__file__).resolve().parent.parent

# Validation data package. Override with EVAONLINE_VALIDATION_DIR if it lives
# elsewhere.
DATA_PKG = Path(
    os.environ.get(
        "EVAONLINE_VALIDATION_DIR",
        REPO_ROOT / "EVAonline_validation",
    )
)

DATA = DATA_PKG / "data"
CACHE_DIR = DATA / "6_validation_full_pipeline" / "xavier_validation" / "cache"
XAVIER_DIR = DATA / "original_data" / "eto_xavier_csv"
FINAL_SUMMARY = (
    DATA / "6_validation_full_pipeline" / "xavier_validation" / "FINAL_SUMMARY.csv"
)
SENSITIVITY_WEIGHTS = DATA / "analysis_results" / "sensitivity_weights.csv"
SENSITIVITY_KALMAN = DATA / "analysis_results" / "sensitivity_kalman_params.csv"

OUTPUTS = REPO_ROOT / "validation" / "outputs"

# ---- Canonical study-design constants (single source of truth) -------------
N_SITES = 17
N_DAYS_PER_SITE = 10_958          # 1991-01-01 .. 2020-12-31 (30 yr)
N_OBS = N_SITES * N_DAYS_PER_SITE  # 186_286 total daily observations

CALIB_YEARS = (1991, 2010)        # temporal-split training window
VALID_YEARS = (2011, 2020)        # temporal-split held-out window


def require_data() -> None:
    """Fail early with a clear message if the data package is missing."""
    if not CACHE_DIR.exists():
        raise SystemExit(
            "Validation data not found.\n"
            f"  expected: {CACHE_DIR}\n"
            "  set EVAONLINE_VALIDATION_DIR to the EVAonline_validation path."
        )


def ensure_outputs() -> Path:
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    return OUTPUTS
