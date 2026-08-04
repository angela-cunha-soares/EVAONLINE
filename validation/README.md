# EVAonline — Supplementary validation

Reproducible scripts that regenerate the supplementary tables and figures
reported in the *Environmental Modelling & Software* article
(https://doi.org/10.1016/j.envsoft.2026.107113). Every metric comes from a
single tested module (`metrics.py`), so all artefacts share one definition of
KGE / NSE / R2 / MAE / RMSE / PBIAS.

## Data dependency

The heavy dataset (cached daily ET0, Xavier BR-DWGD reference, sensitivity
CSVs) lives in the `EVAonline_validation/` deposit (archived on Zenodo, not
tracked by git). Point to it with:

```bash
export EVAONLINE_VALIDATION_DIR="/path/to/EVAonline_validation"
```

## Layout

| File | Purpose |
|------|---------|
| `metrics.py` | KGE, NSE, R2, MAE, RMSE, bias, PBIAS (NumPy only, unit-tested) |
| `config.py` | Paths + canonical constants (`N_OBS = 186_286`) |
| `data_loader.py` | Loads paired (estimate, Xavier) daily series for the 17 sites |
| `pipeline.py` | Vectorised EVAonline pipeline (toggleable components for the ablation) |
| `cross_validation.py` | Temporal split (1991-2010 / 2011-2020) + leave-one-site-out recalibration |
| `sitewise_metrics.py` | Site-wise metrics (median / IQR / min-max across 17 sites) |
| `persite_table.py` | Full per-site validation table (LaTeX body) |
| `figure_error_boxplots.py` | Error boxplots annotated with site-wise median R2/KGE/NSE |
| `ablation.py` | Component ablation (A1-A5) |
| `outputs/` | Generated CSVs, LaTeX snippets and figures |
| `tests/` | `pytest` unit tests for the metrics |

## Run

```bash
python -m validation.sitewise_metrics
python -m pytest validation/tests -q
```
