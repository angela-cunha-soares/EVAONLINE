"""Vectorised EVAonline pipeline for reviewer-response experiments.

Self-contained re-implementation of the two-stage pipeline used in production
(``backend/core/data_processing``), kept here so the validation experiments are
reproducible without a running backend:

  Stage 1 - region-adaptive weighted fusion of NASA POWER + Open-Meteo
  FAO-56  - vectorised Penman-Monteith ET0
  Stage 2 - adaptive Kalman with monthly bias correction + climatological priors

The numerics mirror ``sensitivity_weights.py`` / ``sensitivity_kalman_params.py``
from the validation dataset (same constants), but with configurable knobs so the
ablation (R1-C7) and cross-validation (R1-C1) scripts can toggle components.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from validation import config

# Variables fused in Stage 1. Only the first six enter FAO-56; precipitation is
# carried for the Kalman precip filter but does not affect ET0.
ETO_VARS = ["T2M_MAX", "T2M_MIN", "T2M", "RH2M", "WS2M", "ALLSKY_SFC_SW_DWN"]
FUSE_VARS = ETO_VARS + ["PRECTOTCORR"]

# Baseline Stage-1 NASA weights (production HIST_WEIGHTS). OpenMeteo gets 1 - w.
BASELINE_WEIGHTS = {
    "T2M_MAX": 0.58,
    "T2M_MIN": 0.52,
    "T2M": 0.60,
    "RH2M": 0.35,
    "WS2M": 0.20,
    "ALLSKY_SFC_SW_DWN": 0.92,
    "PRECTOTCORR": 0.50,
}

# Baseline Kalman hyperparameters.
BASELINE_KALMAN = {
    "q_ratio": 0.08,
    "r_base_sq": 0.55 ** 2,
    "lower_factor": 0.80,
    "upper_factor": 1.25,
    "innov_threshold": 1.50,
    "q_inflation": 1.80,
}

_GSC, _SIGMA, _ALBEDO = 0.0820, 4.903e-9, 0.23
_HISTORICAL_DIR = config.DATA / "original_data" / "historical" / "cities"


# --------------------------------------------------------------------------- #
# FAO-56 Penman-Monteith (vectorised)
# --------------------------------------------------------------------------- #
def _wind_2m(u: np.ndarray, height: float) -> np.ndarray:
    if height == 2.0:
        return np.maximum(u, 0.5)
    return np.maximum(u * (4.87 / np.log(67.8 * height - 5.42)), 0.5)


def calc_eto(df: pd.DataFrame, lat: float, elev: float) -> np.ndarray:
    """ET0 (mm/day) from fused daily meteorology. Wind already at 2 m."""
    Tmax, Tmin, Tmean = df["T2M_MAX"].values, df["T2M_MIN"].values, df["T2M"].values
    RH = df["RH2M"].values
    Rs = np.maximum(df["ALLSKY_SFC_SW_DWN"].values, 0.1)
    u2 = np.maximum(df["WS2M"].values, 0.5)
    doy = pd.to_datetime(df["date"]).dt.dayofyear.astype(float).values

    es = 0.5 * (0.6108 * np.exp(17.27 * Tmax / (Tmax + 237.3))
                + 0.6108 * np.exp(17.27 * Tmin / (Tmin + 237.3)))
    ea = (RH / 100.0) * es
    vpd = np.maximum(es - ea, 0.01)

    phi = np.radians(lat)
    dr = 1 + 0.033 * np.cos(2 * np.pi * doy / 365)
    decl = 0.409 * np.sin(2 * np.pi * doy / 365 - 1.39)
    ws = np.arccos(np.clip(-np.tan(phi) * np.tan(decl), -1, 1))
    Ra = np.maximum((1440 / np.pi) * _GSC * dr
                    * (ws * np.sin(phi) * np.sin(decl)
                       + np.cos(phi) * np.cos(decl) * np.sin(ws)), 0.0)
    Rso = (0.75 + 2e-5 * elev) * Ra
    ratio = np.divide(Rs, Rso, out=np.ones_like(Rs), where=Rso > 1e-6)
    fcd = np.clip(1.35 * ratio - 0.35, 0.3, 1.0)
    Rnl = (_SIGMA * ((Tmax + 273.15) ** 4 + (Tmin + 273.15) ** 4) / 2
           * (0.34 - 0.14 * np.sqrt(np.maximum(ea, 0.01))) * fcd)
    Rn = (1 - _ALBEDO) * Rs - Rnl

    slope = (4098 * 0.6108 * np.exp(17.27 * Tmean / (Tmean + 237.3))
             / (Tmean + 237.3) ** 2)
    pressure = 101.3 * ((293.0 - 0.0065 * elev) / 293.0) ** 5.26
    gamma = 0.000665 * pressure

    num = 0.408 * slope * Rn + gamma * (900 / (Tmean + 273.15)) * u2 * vpd
    den = slope + gamma * (1 + 0.34 * u2)
    return np.maximum(np.where(den > 1e-6, num / den, 0.0), 0.0)


# --------------------------------------------------------------------------- #
# Stage 1: weighted fusion
# --------------------------------------------------------------------------- #
def fuse_variables(
    nasa: pd.DataFrame, om: pd.DataFrame, weights: dict[str, float]
) -> pd.DataFrame:
    """Fuse NASA + Open-Meteo. OM wind (10 m) is converted to 2 m first."""
    out = nasa[["date"]].copy()
    for var in FUSE_VARS:
        w_n = weights.get(var, 0.5)
        n_vals = nasa[var].values
        if var == "WS2M" and "WS10M" in om.columns:
            o_vals = _wind_2m(om["WS10M"].values, 10.0)
        else:
            o_vals = om[var].values
        if var == "PRECTOTCORR":
            out[var] = 0.5 * (n_vals + o_vals)
        else:
            out[var] = w_n * n_vals + (1.0 - w_n) * o_vals
    return out


# --------------------------------------------------------------------------- #
# Stage 2: parameterised adaptive Kalman
# --------------------------------------------------------------------------- #
class ParameterisedKalman:
    """Adaptive Kalman with tunable knobs (mirrors AdaptiveKalmanFilter)."""

    def __init__(self, normal=5.0, std=1.0, p01=None, p99=None, *,
                 q_ratio=0.08, r_base_sq=0.3025, lower_factor=0.80,
                 upper_factor=1.25, innov_threshold=1.5, q_inflation=1.8,
                 dynamic_q=True):
        self.normal = float(normal)
        self.std = max(float(std), 0.4)
        self.p01 = p01 if p01 is not None else normal - 3.5 * self.std
        self.p99 = p99 if p99 is not None else normal + 3.5 * self.std
        self.R_base = float(r_base_sq)
        self.Q = self.std ** 2 * q_ratio
        self.lower_factor, self.upper_factor = lower_factor, upper_factor
        self.innov_threshold, self.q_inflation = innov_threshold, q_inflation
        self.dynamic_q = dynamic_q
        self.last_error, self.estimate, self.error = 0.0, normal, self.std ** 2

    def update(self, z: float) -> float:
        if np.isnan(z):
            return self.estimate
        if z < self.p01 * self.lower_factor or z > self.p99 * self.upper_factor:
            R = self.R_base * 500
        elif z < self.p01 or z > self.p99:
            R = self.R_base * 50
        else:
            R = self.R_base
        if self.dynamic_q:
            current_error = abs(z - self.estimate)
            if current_error > self.last_error * self.innov_threshold:
                self.Q = min(self.Q * self.q_inflation, self.std ** 2 * 0.5)
            self.last_error = current_error
        priori_err = self.error + self.Q
        K = priori_err / (priori_err + R)
        self.estimate = self.estimate + K * (z - self.estimate)
        self.error = (1 - K) * priori_err
        return round(self.estimate, 3)


def apply_kalman_eto(eto_raw, dates, ref, kalman_kwargs, *, use_priors=True,
                     use_bias=True, use_bounds=True):
    """3-step ET0 Kalman (bias -> correction -> continuous filter).

    Component switches (for the R1-C7 ablation, isolating one effect each):
      use_priors : master switch. False => simplified mode (no climatological
                   anchoring at all: no bias correction, no p01/p99 bounds).
      use_bias   : apply the monthly climatological bias correction.
      use_bounds : apply the p01/p99 soft bounds that inflate R on outliers.
      kalman_kwargs["dynamic_q"]/["q_inflation"] : dynamic process-noise.
    """
    eto_raw = np.asarray(eto_raw, dtype=float)
    months = dates.dt.month.values

    if not use_priors:
        kf = ParameterisedKalman(normal=5.0, std=1.0, p01=-1e9, p99=1e9,
                                 **{**kalman_kwargs, "dynamic_q": False})
        out = np.full(len(eto_raw), np.nan)
        for i, z in enumerate(eto_raw):
            if not np.isnan(z):
                out[i] = kf.update(z)
        return out

    if use_bias:
        monthly_bias = {}
        for m in range(1, 13):
            mask = months == m
            if mask.any():
                monthly_bias[m] = np.nanmean(eto_raw[mask]) - ref["eto_normals"].get(m, 5.0)
            else:
                monthly_bias[m] = 0.0
        corrected = np.array([
            z - monthly_bias.get(months[i], 0.0) if not np.isnan(z) else np.nan
            for i, z in enumerate(eto_raw)
        ])
    else:
        corrected = eto_raw.copy()

    annual_normal = float(np.mean(list(ref["eto_normals"].values())))
    annual_std = float(np.mean(list(ref["eto_stds"].values())))
    kf = ParameterisedKalman(normal=annual_normal, std=annual_std,
                             p01=None, p99=None, **kalman_kwargs)
    out = np.full(len(eto_raw), np.nan)
    for i, z in enumerate(corrected):
        if not np.isnan(z):
            m = months[i]
            if use_bounds:
                kf.p01 = ref["eto_p01"].get(m, 0)
                kf.p99 = ref["eto_p99"].get(m, 10)
            else:
                kf.p01, kf.p99 = -1e9, 1e9  # disable outlier R-inflation
            out[i] = kf.update(z)
    return out


# --------------------------------------------------------------------------- #
# Data access
# --------------------------------------------------------------------------- #
def load_priors(city: str) -> dict | None:
    path = _HISTORICAL_DIR / f"report_{city}.json"
    if not path.exists():
        return None
    monthly = json.loads(path.read_text(encoding="utf-8"))[
        "climate_normals_all_periods"]["1991-2020"]["monthly"]
    return {
        "eto_normals": {int(m): float(v.get("normal", 5.0)) for m, v in monthly.items()},
        "eto_stds": {int(m): max(float(v.get("daily_std", 1.0)), 0.5) for m, v in monthly.items()},
        "eto_p01": {int(m): float(v.get("p01", 2.0)) for m, v in monthly.items()},
        "eto_p99": {int(m): float(v.get("p99", 8.0)) for m, v in monthly.items()},
    }


@dataclass
class CityData:
    city: str
    lat: float
    elev: float
    nasa: pd.DataFrame
    om: pd.DataFrame
    dates: pd.Series
    ref_eto: np.ndarray
    priors: dict | None = field(default=None, repr=False)


def load_cities(brazil_only: bool = True) -> dict[str, CityData]:
    """Load aligned NASA/OM/Xavier series + priors for every validation site."""
    config.require_data()
    info = pd.read_csv(config.DATA / "info_cities.csv")
    if brazil_only:
        info = info[info["region"] == "brasil"]
    nasa_dir = config.DATA / "original_data" / "nasa_power_raw"
    om_dir = config.DATA / "original_data" / "open_meteo_raw"

    cities: dict[str, CityData] = {}
    for _, r in info.iterrows():
        city = r["city"]
        nf = nasa_dir / f"{city}_1991-01-01_2020-12-31_NASA_RAW.csv"
        of = om_dir / f"{city}_1991-01-01_2020-12-31_OpenMeteo_RAW.csv"
        xf = config.XAVIER_DIR / f"{city}.csv"
        if not all(p.exists() for p in (nf, of, xf)):
            continue
        nasa = pd.read_csv(nf, parse_dates=["date"])
        om = pd.read_csv(of, parse_dates=["date"])
        xav = pd.read_csv(xf, parse_dates=["date"])
        common = set(nasa.date) & set(om.date) & set(xav.date)
        nasa = nasa[nasa.date.isin(common)].sort_values("date").reset_index(drop=True)
        om = om[om.date.isin(common)].sort_values("date").reset_index(drop=True)
        xav = xav[xav.date.isin(common)].sort_values("date").reset_index(drop=True)
        cities[city] = CityData(
            city=city, lat=float(r["lat"]), elev=float(r["alt"]),
            nasa=nasa, om=om, dates=pd.to_datetime(nasa["date"]),
            ref_eto=xav["eto_xavier"].values, priors=load_priors(city),
        )
    return cities


def run_pipeline(cd: CityData, weights: dict[str, float], kalman_kwargs: dict,
                 *, use_priors: bool = True, use_bias: bool = True,
                 use_bounds: bool = True) -> np.ndarray:
    """Full Stage1 + FAO-56 + Stage2 ET0 series for one city."""
    fused = fuse_variables(cd.nasa, cd.om, weights)
    eto_raw = calc_eto(fused, cd.lat, cd.elev)
    if cd.priors is None:
        return eto_raw
    return apply_kalman_eto(eto_raw, cd.dates, cd.priors, kalman_kwargs,
                            use_priors=use_priors, use_bias=use_bias,
                            use_bounds=use_bounds)
