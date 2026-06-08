"""Reviewer 1, comment 6: regenerate Figure 4 with R2/KGE/NSE annotations.

Daily ET0 error (estimated - reference) boxplots for the four sources, each box
annotated with the *site-wise median* R2, KGE and NSE (Reviewer 1 asked for the
same key metrics shown elsewhere). Site-wise metrics are read from the
per-city comparison table; daily errors are pooled across the 17 sites.

Outputs: r1c6_fig04_error_boxplots.pdf / .png
Run:     python -m validation.r1c6_figure4
"""

from __future__ import annotations

import glob
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from validation import config  # noqa: E402

# (label, source-key in COMPARISON_ALL_SOURCES, daily-error loader name)
SOURCES = [
    ("NASA POWER", "NASA_ONLY", "nasa"),
    ("Open-Meteo Archive", "OPENMETEO_ONLY", "om_calc"),
    ("Open-Meteo API", "OPENMETEO_API", "om_api"),
    ("EVAonline Fusion", "EVAONLINE_FUSION", "eva"),
]
COMPARISON = config.DATA / "7_comparison_all_sources" / "COMPARISON_ALL_SOURCES.csv"


def _xavier() -> dict[str, pd.DataFrame]:
    out = {}
    for f in glob.glob(str(config.XAVIER_DIR / "*.csv")):
        city = os.path.basename(f)[:-4]
        out[city] = pd.read_csv(f, parse_dates=["date"]).rename(
            columns={"eto_xavier": "obs"})[["date", "obs"]]
    return out


def _daily_errors(loader: str, xav: dict) -> np.ndarray:
    """Pooled daily (estimate - reference) errors across all sites."""
    errs = []
    if loader in ("nasa", "om_calc"):
        path = (config.DATA / ("4_eto_nasa_only" if loader == "nasa"
                else "4_eto_openmeteo_only")
                / ("ALL_CITIES_ETo_NASA_ONLY_1991_2020.csv" if loader == "nasa"
                   else "ALL_CITIES_ETo_OpenMeteo_ONLY_1991_2020.csv"))
        df = pd.read_csv(path, parse_dates=["date"])
        col = "eto_evaonline"  # single-source ET0 (column is misnamed upstream)
        for city, g in df.groupby("city"):
            if city not in xav:
                continue
            m = g[["date", col]].merge(xav[city], on="date").dropna()
            errs.append((m[col] - m["obs"]).values)
    elif loader == "om_api":
        for f in glob.glob(str(config.DATA / "original_data" / "eto_open_meteo"
                                / "*_OpenMeteo_ETo.csv")):
            city = os.path.basename(f).replace("_OpenMeteo_ETo.csv", "")
            if city not in xav:
                continue
            d = pd.read_csv(f, parse_dates=["date"])
            m = d.merge(xav[city], on="date").dropna()
            errs.append((m["eto_openmeteo"] - m["obs"]).values)
    elif loader == "eva":
        for f in glob.glob(str(config.CACHE_DIR / "*_eto_final.csv")):
            city = os.path.basename(f).replace("_eto_final.csv", "")
            if city not in xav:
                continue
            d = pd.read_csv(f, parse_dates=["date"])[["date", "eto_final"]]
            m = d.merge(xav[city], on="date").dropna()
            errs.append((m["eto_final"] - m["obs"]).values)
    return np.concatenate(errs) if errs else np.array([])


def _sitewise_medians() -> pd.DataFrame:
    cmp = pd.read_csv(COMPARISON)
    return cmp.groupby("source")[["r2", "kge", "nse"]].median()


def main() -> None:
    out = config.ensure_outputs()
    config.require_data()
    xav = _xavier()
    med = _sitewise_medians()

    data, labels, medians = [], [], []
    for label, key, loader in SOURCES:
        e = _daily_errors(loader, xav)
        data.append(e)
        labels.append(label)
        medians.append(np.median(e))
        print(f"  {label:<20s} n={e.size:>7,}  median err={np.median(e):+.2f} mm/d")

    fig, ax = plt.subplots(figsize=(9, 5.5))
    bp = ax.boxplot(data, showfliers=False, patch_artist=True, widths=0.6)
    colors = ["#d9772b", "#5b8db8", "#7ba05b", "#b5446e"]
    for patch, c in zip(bp["boxes"], colors):
        patch.set_facecolor(c)
        patch.set_alpha(0.55)
    for med_line in bp["medians"]:
        med_line.set_color("black")
        med_line.set_linewidth(1.5)

    ax.axhline(0.0, color="grey", ls="--", lw=1, zorder=0)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylabel(r"Daily ET$_0$ error (estimated $-$ reference) [mm d$^{-1}$]")

    ymax = max(np.percentile(d, 98) for d in data) * 1.05
    ymin = min(np.percentile(d, 2) for d in data) * 1.05
    ax.set_ylim(ymin, ymax + 0.9)
    for i, (label, key, _) in enumerate(SOURCES, start=1):
        r = med.loc[key]
        txt = (f"$R^2$={r['r2']:.2f}\nKGE={r['kge']:.2f}\nNSE={r['nse']:.2f}\n"
               f"med={medians[i-1]:+.2f}")
        ax.text(i, ymax + 0.05, txt, ha="center", va="bottom", fontsize=8,
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="grey", alpha=0.85))

    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(out / f"r1c6_fig04_error_boxplots.{ext}", dpi=200,
                    bbox_inches="tight")
    plt.close(fig)
    print(f"\nFigure written to {out}")


if __name__ == "__main__":
    main()
