# EVAonline — Reviewer-response validation

Reproducible scripts that regenerate the tables/figures requested by the
reviewers of the *Environmental Modelling & Software* submission. Every metric
comes from a single tested module (`metrics.py`), so all artefacts share one
definition of KGE/NSE/R²/MAE/RMSE/PBIAS.

## Data dependency

The heavy dataset (cached daily ET₀, Xavier BR-DWGD reference, sensitivity
CSVs) lives in `EVAonline_validation_v1.0.0/` (not git-tracked). Point to it
with the env var if it sits elsewhere:

```powershell
$env:EVAONLINE_VALIDATION_DIR = "C:\path\to\EVAonline_validation_v1.0.0"
```

## Layout

| File | Purpose |
|------|---------|
| `metrics.py` | KGE, NSE, R², MAE, RMSE, bias, PBIAS (NumPy only, unit-tested) |
| `config.py` | Paths + canonical constants (`N_OBS = 186_286`, calib/valid windows) |
| `data_loader.py` | Loads paired (estimate, Xavier) daily series for the 17 sites |
| `r1c2_sitewise.py` | **R1-C2 + R1-C8** — Table 12 site-wise (median/IQR/min-max) |
| `outputs/` | Generated CSVs + `*.tex` snippets (safe to regenerate) |
| `tests/` | `pytest` unit tests for the metrics |

## Reviewer-1 comment → status

| Comment | Deliverable | Status |
|---------|-------------|--------|
| R1-C1 | `r1c1_cross_validation.py` — temporal split + LOSO (real recalibration) | ✅ done — supports draft |
| R1-C2 | `r1c2_sitewise.py` → `r1c2_table12.tex` | ✅ done |
| R1-C6 | `r1c6_figure4.py` — Figure 4 with R²/KGE/NSE panel | ✅ done |
| R1-C7 | `r1c7_ablation.py` (A1–A4) | ⚠️ done — **contradicts draft** (see REVIEWER1_RESPONSE.md) |
| R1-C8 | `N_OBS = 186_286` enforced in `config.py` (asserted at runtime) | ✅ done |
| R1-C3/4/5/9 | Manuscript-only (LaTeX ready in `docs/CORRECOES.md`) | text only |

See **`REVIEWER1_RESPONSE.md`** for the point-by-point response with all
regenerated numbers and the two open decisions for the author.

## Run

```bash
python -m validation.r1c2_sitewise
python -m pytest validation/tests -q
```
