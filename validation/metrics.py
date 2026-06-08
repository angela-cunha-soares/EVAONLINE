"""Hydrological goodness-of-fit metrics for ET0 validation.

All functions take ``sim`` (estimated/simulated) and ``obs`` (reference /
observed) as 1-D array-likes of equal length, drop pairwise NaNs, and return
a scalar ``float``. They are deliberately dependency-light (NumPy only) so the
same definitions back every reviewer-response script and can be unit-tested
against textbook values.

Definitions follow:
- KGE: Gupta et al. (2009), J. Hydrol. 377, 80-91 (2009 formulation).
- NSE: Nash & Sutcliffe (1970), J. Hydrol. 10, 282-290.
- R2 : square of the Pearson correlation coefficient.
- PBIAS: percent bias (Moriasi et al., 2007), positive => overestimation.
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "align",
    "r2",
    "kge",
    "nse",
    "mae",
    "rmse",
    "bias",
    "pbias",
    "all_metrics",
]


def align(sim, obs) -> tuple[np.ndarray, np.ndarray]:
    """Return paired finite arrays, dropping any index where either is NaN."""
    sim = np.asarray(sim, dtype=float)
    obs = np.asarray(obs, dtype=float)
    if sim.shape != obs.shape:
        raise ValueError(
            f"sim/obs length mismatch: {sim.shape} vs {obs.shape}"
        )
    mask = np.isfinite(sim) & np.isfinite(obs)
    if mask.sum() < 2:
        raise ValueError("fewer than 2 valid paired observations")
    return sim[mask], obs[mask]


def r2(sim, obs) -> float:
    """Coefficient of determination (squared Pearson correlation)."""
    s, o = align(sim, obs)
    r = np.corrcoef(s, o)[0, 1]
    return float(r * r)


def kge(sim, obs) -> float:
    """Kling-Gupta Efficiency (Gupta et al., 2009)."""
    s, o = align(sim, obs)
    r = np.corrcoef(s, o)[0, 1]
    alpha = s.std(ddof=0) / o.std(ddof=0)  # variability ratio
    beta = s.mean() / o.mean()             # bias ratio
    return float(1.0 - np.sqrt((r - 1) ** 2 + (alpha - 1) ** 2 + (beta - 1) ** 2))


def nse(sim, obs) -> float:
    """Nash-Sutcliffe Efficiency."""
    s, o = align(sim, obs)
    denom = np.sum((o - o.mean()) ** 2)
    if denom == 0:
        return float("nan")
    return float(1.0 - np.sum((s - o) ** 2) / denom)


def mae(sim, obs) -> float:
    """Mean absolute error (same units as the variable)."""
    s, o = align(sim, obs)
    return float(np.mean(np.abs(s - o)))


def rmse(sim, obs) -> float:
    """Root mean squared error (same units as the variable)."""
    s, o = align(sim, obs)
    return float(np.sqrt(np.mean((s - o) ** 2)))


def bias(sim, obs) -> float:
    """Mean bias (sim - obs)."""
    s, o = align(sim, obs)
    return float(np.mean(s - o))


def pbias(sim, obs) -> float:
    """Percent bias; positive means the estimate overshoots the reference."""
    s, o = align(sim, obs)
    total = np.sum(o)
    if total == 0:
        return float("nan")
    return float(100.0 * np.sum(s - o) / total)


def all_metrics(sim, obs) -> dict[str, float]:
    """Convenience wrapper returning every metric in one dict."""
    return {
        "r2": r2(sim, obs),
        "kge": kge(sim, obs),
        "nse": nse(sim, obs),
        "mae": mae(sim, obs),
        "rmse": rmse(sim, obs),
        "bias": bias(sim, obs),
        "pbias": pbias(sim, obs),
    }
