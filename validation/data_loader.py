"""Load paired (EVAonline estimate, Xavier BR-DWGD reference) daily series.

Reads the cached per-city pipeline output and the Xavier reference, returning
one tidy long DataFrame: columns [city, date, sim, obs]. This is the common
input for the site-wise, cross-validation, and ablation scripts.
"""

from __future__ import annotations

import glob
import os

import pandas as pd

from validation import config


def load_paired(estimate_col: str = "eto_final") -> pd.DataFrame:
    """Return long DataFrame [city, date, sim, obs] across all 17 sites."""
    config.require_data()
    frames = []
    for path in sorted(glob.glob(str(config.CACHE_DIR / "*_eto_final.csv"))):
        city = os.path.basename(path).replace("_eto_final.csv", "")
        xpath = config.XAVIER_DIR / f"{city}.csv"
        if not xpath.exists():
            continue
        sim = pd.read_csv(path, parse_dates=["date"])[["date", estimate_col]]
        obs = pd.read_csv(xpath, parse_dates=["date"]).rename(
            columns={"eto_xavier": "obs"}
        )[["date", "obs"]]
        merged = sim.merge(obs, on="date").rename(columns={estimate_col: "sim"})
        merged.insert(0, "city", city)
        frames.append(merged.dropna(subset=["sim", "obs"]))
    if not frames:
        raise SystemExit("No paired city files were loaded; check data paths.")
    return pd.concat(frames, ignore_index=True)
