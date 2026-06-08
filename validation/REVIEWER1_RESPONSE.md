# Reviewer 1 — point-by-point response (reproducible artefacts)

All numbers below are produced by the scripts in this folder from the
`EVAonline_validation_v1.0.0` dataset. Regenerate everything with:

```bash
python -m validation.r1c2_sitewise          # R1-C2, R1-C8
python -m validation.r1c1_cross_validation   # R1-C1
python -m validation.r1c7_ablation           # R1-C7
python -m validation.r1c6_figure4            # R1-C6
python -m pytest validation/tests -q
```

Status legend: ✅ done & supports manuscript · ⚠️ done but **contradicts** the
current draft (decision needed) · 📄 manuscript-only text (ready in
`docs/CORRECOES.md`).

---

## R1-C1 — calibration/validation independence ✅
**Deliverable:** `r1c1_cross_validation.py` → `outputs/r1c1_cv.tex`,
`r1c1_cv_independent.csv`, `r1c1_calibrated_weights.json`.

Weights are **really re-optimised** (L-BFGS-B, MAE objective) on the training
fold only; the held-out fold runs the full pipeline. Results match the draft and
support the claim:

| Scheme | R² | KGE | NSE | MAE | RMSE |
|---|---|---|---|---|---|
| In-sample (1991–2020) | 0.719±0.069 | 0.813±0.059 | 0.710±0.069 | 0.403 | 0.536 |
| Temporal split (test 2011–2020) | 0.727±0.074 | 0.811±0.054 | 0.712±0.076 | 0.411 | 0.555 |
| LOSO (17 folds) | 0.702±0.070 | 0.803±0.064 | 0.686±0.077 | 0.421 | 0.558 |

KGE drop in-sample → LOSO = **−0.011** (≪ 0.05) → generalises across unseen
sites/years. Paste `r1c1_cv.tex` into Table cv-independent.

## R1-C2 — site-wise aggregation ✅
**Deliverable:** `r1c2_sitewise.py` → `outputs/r1c2_table12.tex`,
`r1c2_sitewise_summary.csv`. Metrics computed per site, then median/IQR/min–max.

| Metric | median (IQR) [min,max] |
|---|---|
| R² | 0.69 (0.65, 0.75) [0.55, 0.79] |
| KGE | 0.81 (0.79, 0.86) [0.72, 0.89] |
| NSE | 0.68 (0.63, 0.74) [0.51, 0.79] |

**Fix the table note:** the lowest-KGE site is **Imperatriz_MA (0.721)**, not
Campos Lindos.

## R1-C6 — Figure 4 with R²/KGE/NSE ✅
**Deliverable:** `r1c6_figure4.py` → `outputs/r1c6_fig04_error_boxplots.pdf`.
Each box now carries the site-wise median R²/KGE/NSE and the median error.
Pooled daily median errors: NASA +0.47, OM-Archive +0.39, OM-API +0.36,
**EVAonline +0.00** mm d⁻¹.
> Note: these pooled medians (+0.47/+0.39/+0.36/+0.00) differ from the draft
> caption (+0.69/+0.55/+0.51/+0.03). Use the regenerated values for consistency.

## R1-C7 — ablation ✅ (component-isolated)
**Deliverable:** `r1c7_ablation.py` → `outputs/r1c7_ablation.tex`.

Each ablation removes ONE component, holding the rest at baseline. This clean
decomposition **supports the current Section 3.1.3 narrative** (radiation is a
primary driver) while adding the quantitative evidence the reviewer asked for:

| Config | KGE | PBIAS (%) | ΔKGE | role |
|---|---|---|---|---|
| Baseline | 0.812 | +0.36 | — | full pipeline |
| A1: R_s Open-Meteo only (no CERES) | 0.756 | +0.51 | −0.056 | Stage-1 radiation weighting |
| **A2: R_s → climatology** | 0.637 | −0.41 | **−0.175** | R_s daily variability (largest) |
| A3: no bias correction | 0.722 | +10.87 | −0.091 | climatological anchoring → keeps PBIAS≈0 |
| A4: no outlier rejection (p01/p99) | 0.809 | −0.00 | −0.003 | robustness on extreme days only |
| A5: no dynamic Q | 0.706 | +0.22 | −0.106 | tracks sharp transitions |

Reading: **solar radiation is the dominant input** (A1+A2), confirming the
section's thesis; the **climatological bias correction** is what holds PBIAS near
zero (without it PBIAS jumps to +10.9 %); **dynamic Q** matters for transitions;
the **p01/p99 outlier rejection** has a small *aggregate* effect (it only acts on
a handful of extreme days, so KGE over 30 yr barely moves).

> The earlier draft table in `docs/CORRECOES.md` (A3 −0.066, A4 −0.016) used
> different/placeholder definitions and a 4-row layout. Replace it with
> `r1c7_ablation.tex` and the 5-row design above. A ready-to-paste rewrite of
> the subsection is in `outputs/r1c7_section_3.1.3.tex`.

## R1-C8 — consistent sample size ✅
Canonical value enforced in `config.py`: **N_OBS = 186 286** (17 × 10 958),
asserted at runtime in `r1c2_sitewise.py`. The dataset README itself has the
inconsistency (line 13 = 186,287; line 723 = 186,286) — fix to **186,286** in
Abstract, Highlights, Graphical Abstract and Section 3.1.

## R1-C3 / C4 / C5 / C9 — manuscript text 📄
Pure LaTeX edits, already drafted in `docs/CORRECOES.md`:
- **C3:** split the limitations paragraph into data-level vs infrastructure-level.
- **C4:** number the architecture tiers (1)–(4).
- **C5:** move the two-Open-Meteo-pathways sentence to Section 2.1.
- **C9:** moderate the "globally scalable" / "virtual weather station" claims;
  add the scope-of-validation limitations paragraph.

---

## Open decisions for the author
1. **R1-C6 medians** — confirm switching the Figure 4 caption to the regenerated
   pooled medians (+0.47/+0.39/+0.36/+0.00 mm d⁻¹).
2. **Send the full paper** if you want the rewrites made consistent with the
   surrounding sections, equation/table/figure numbering and citation keys.
