![Coverage](https://img.shields.io/badge/coverage-86.5%25-brightgreen) ![Tests](https://img.shields.io/badge/tests-2800%20passed-blue)
# 🌦️ **EVAonline** 

#### _An open-source web platform for global reference evapotranspiration estimation via multi-source data fusion_

EVAonline is a comprehensive web platform for estimating reference evapotranspiration (ET₀) using the **FAO-56 Penman-Monteith** method. It integrates real-time meteorological data from multiple global sources through a **two-stage data fusion** approach—region‑adaptive weighted averaging followed by Kalman smoothing—to deliver accurate, bias‑corrected daily ET₀. Built with Dash + FastAPI, it provides interactive dashboards, WebSocket progress tracking, water‑deficit analysis, and full bilingual support (EN/PT).

For a detailed description of the methodology and case studies, please refer to our Zenodo [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.17791397.svg)](https://doi.org/10.5281/zenodo.17791397)

---

## 📚 Materials and Methods

### 1. Climate Data Sources

EVAonline integrates meteorological data from **six publicly available APIs** provided by four institutions. The table below summarises their coverage, resolution, and the underlying models. All sources are harmonised into a common internal schema that contains the seven variables required by the FAO‑56 Penman‑Monteith.

| **Source**                | **Model**                         | **Coverage**                | **Resolution** |
|---------------------------|-----------------------------------|-----------------------------|----------------|
| **NASA POWER**            | MERRA-2 + CERES                   | Global, 1981–present        | 0.5°           |
| **Open‑Meteo Archive**    | Best match (ERA5-Land / ERA5)     | Global, 1940–present        | 9–25 km        |
| **Open‑Meteo Forecast**   | Best match (multi‑NWP)            | Global, 16 days             | 1–25 km        |
| **MET Norway**            | MEPS / ECMWF IFS                  | Global, 9–10 days           | 2.5–9 km       |
| **NWS Forecast**          | Blend of NWP (GFS, NAM, HRRR)     | CONUS, 7 days               | 2.5 km         |
| **NWS Stations**          | In‑situ observations (ASOS)       | CONUS, ~900 active stations | Station        |

*Notes:* Historical queries begin on 01/01/1990; the forecast horizon is limited to today + 5 days (6 days total).

---

### 2. Data Preprocessing & Quality Control

- **Cleaning & harmonisation:** Sub‑daily data are aggregated to daily resolution. Missing/invalid values are replaced with `NaN`.
- **Quality control (3 steps):**  
  1. **Physical range validation** using region‑specific bounds (WMO, BR‑DWGD).  
  2. **Outlier detection** via adaptive IQR (strict: 1.2; default: 1.5; lenient: 2.25).  
  3. **Circuit‑breaker:** Sources with a quality score (QS) < 60% are excluded from fusion for that request.
- **Imputation cascade:** (i) bidirectional linear interpolation; (ii) forward‑fill; (iii) backward‑fill; (iv) column mean as last resort.
- **Elevation & wind correction:** Elevation from user input, OpenTopoData, or sea level; wind speed adjusted to 2 m using FAO‑56 Eq. 47.

---

### 3. Multi‑Source Data Fusion (Two‑Stage)

#### _Stage 1 – Region‑Adaptive Weighted Averaging_
For each variable and day, a weighted average is computed over available “healthy” sources (QS ≥ 60%). Weights are calibrated against the BR‑DWGD dataset (1991–2020) for historical mode, and region‑dependent for forecast mode.

**Historical / Recent mode (global):** NASA POWER + Open‑Meteo Archive.  
Example weights (calibrated): $R_s$: 0.92 (NASA), 0.08 (OM); $T_{\text{mean}}$: 0.60 (NASA), 0.40 (OM); $u_2$: 0.20 (NASA), 0.80 (OM).

**Forecast mode (region‑dependent):**  

| Region       | NWS  | Open‑Meteo | MET Norway |
|--------------|------|------------|------------|
| USA          | 0.50 | 0.30       | 0.20       |
| Nordic Europe| —    | 0.20       | 0.80       |
| Global       | —    | 0.70       | 0.30       |

When a source does not provide a variable (e.g., MET Norway lacks $R_s$ in the USA), weights are renormalised among remaining sources.

#### _Stage 2 – Adaptive Kalman Smoothing_

A scalar Kalman filter (random‑walk model) is applied independently to precipitation and ET₀.  
- **Measurement noise $R_k$** is inflated when observations fall outside the 1st–99th monthly percentiles (climatological prior).  
- **Process noise $Q$** is adjusted dynamically based on the innovation magnitude.  
- **Climatological priors** are derived from 27 reference cities (17 in Brazil, 10 globally) to initialise the filter and bound anomalies.

---

### 4. Reference Evapotranspiration Calculation

Daily ET₀ is computed using the FAO‑56 Penman‑Monteith equation:

$$ET_0 = \frac{0.408\,\Delta\,(R_n - G) + \gamma\,\dfrac{900}{T_{\text{mean}}+273}\,u_2\,(e_s - e_a)}{\Delta + \gamma\,(1 + 0.34\,u_2)}$$

Intermediate variables (saturation vapour pressure, actual vapour pressure, net radiation, etc.) follow the standard FAO‑56 procedures. Net radiation uses the Stefan‑Boltzmann approach; clear‑sky radiation $R_{so}$ accounts for elevation.

---

### 5. System Architecture & Implementation

EVAonline follows a **hexagonal (Ports and Adapters)** architecture with a clean domain core. The production deployment is orchestrated by Docker Compose with **13 containerised services**:

- **Reverse proxy:** Nginx (SSL termination, rate limiting).  
- **Application tier:** FastAPI + Dash (Gunicorn/Uvicorn), WebSocket progress via Redis pub/sub.  
- **Task processing:** Celery (gevent for I/O, prefork for CPU‑bound ET₀/Kalman), Celery Beat, Flower monitoring.  
- **Data & infrastructure:** PostgreSQL 16, Redis 7 (cache + broker), Prometheus + Grafana.

The platform is launched with a single `docker compose up` command, which runs Alembic migrations and health checks automatically.

---

### 6. Validation Against BR‑DWGD

We validated EVAonline against the **BR‑DWGD** gridded dataset (1991–2020) across 17 sites (16 in MATOPIBA + Piracicaba/SP), totalling 186,286 daily observations.

| Method                     | $R^2$        | KGE          | NSE           | MAE (mm/d) | RMSE (mm/d) | PBIAS (%) |
|----------------------------|--------------|--------------|---------------|------------|-------------|-----------|
| NASA POWER (FAO‑56)        | 0.740 ± 0.062| 0.411 ± 0.264| -0.363 ± 0.788| 0.845      | 1.117       | +15.78    |
| Open‑Meteo Archive (ERA5‑L)| 0.636 ± 0.173| 0.432 ± 0.413| -0.547 ± 1.820| 0.859      | 1.097       | +13.02    |
| Open‑Meteo API (ERA5)      | 0.649 ± 0.174| 0.584 ± 0.188| 0.216 ± 0.356 | 0.690      | 0.860       | +8.27     |
| **EVAonline Fusion**       | **0.694 ± 0.074** | **0.814 ± 0.053** | **0.676 ± 0.085** | **0.423** | **0.566** | **+0.71** |

- **Systematic bias eliminated:** PBIAS reduced from +15.78% (NASA) to +0.71% (fusion).  
- **Spatial robustness:** KGE > 0.72 at all 17 sites, whereas individual sources showed negative KGE at some locations.  
- **Seasonal improvement:** RMSE reduced by ≈66% during the dry season (May–September).  
- **Error distribution:** Interquartile range compressed by >50% compared to raw satellite/reanalysis products.

---

## 🏗️ Architecture

### Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | Dash 3, Dash Bootstrap Components, dash‑leaflet, Plotly 6 |
| **Backend** | FastAPI, Celery (3 worker types), Redis Pub/Sub |
| **Database** | PostgreSQL 16, Alembic migrations |
| **Cache** | Redis 7 (caching + message broker) |
| **Infra** | Docker Compose (13 services), Nginx, Prometheus + Grafana |
| **i18n** | JSON‑based translations (EN / PT) |
| **CI/Quality** | pytest, black, flake8, mypy, pre‑commit |

---

## 📊 Features

- **FAO‑56 Penman‑Monteith** with 7 input variables (Tmax, Tmin, Tmean, RH, u₂, Rₛ, P).
- **3 operation modes:** Dashboard (quick), Forecast (6‑day), Historical (any period, async email).
- **Multi‑source fusion** with region‑adaptive weights + Kalman smoothing.
- **Automatic ocean/water body detection** to block invalid calculations.
- **Interactive world map** (dash‑leaflet) with city heatmap.
- **Water deficit analysis:** daily balance (P − ET₀), cumulative deficit, area chart.
- **Statistical analysis:** mean, median, SD, IQR, CV%, skewness, kurtosis, Shapiro‑Wilk (requires ≥30 days).
- **Locale‑aware exports:** CSV/Excel with proper separators (PT: `;` / EN: `,`).
- **Real‑time progress** via WebSocket with translated messages.
- **Bilingual support (EN/PT):** all UI strings, documentation, error messages.

---

## 🚀 Getting Started

### Prerequisites
- Docker & Docker Compose v2+
- Python 3.12+ (for local development)
- Git
- General‑purpose computer with internet access (web platform) or server with ≥8GB RAM (Docker deployment)

### Quick Start (Docker)

```bash
# 1. Clone
git clone https://github.com/angela-cunha-soares/EVAONLINE
cd EVAONLINE

# 2. Configure environment
cp .env.example .env
# Edit .env with your database passwords and API keys

# 3. Build and start all services
docker compose up --build -d

# 4. Access the application
#    Dashboard:    http://localhost
#    API docs:     http://localhost/api/v1/docs
#    Grafana:      http://localhost/grafana/
#    Flower:       http://localhost/flower/
```

### Local Development

```bash
# 1. Install dependencies (requires Python 3.12+)
pip install -e ".[dev]"

# 2. Start only database + cache
docker compose up postgres redis -d

# 3. Run API server
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# 4. Run Celery worker
celery -A backend.infrastructure.celery.celery_config worker --loglevel=info --pool=solo
```

---


## 🔧 Configuration

### Environment Variables

Key configuration options in `.env`:

| Variable | Description |
|---|---|
| `POSTGRES_*` | PostgreSQL connection settings |
| `REDIS_*` | Redis cache and broker settings |
| `FASTAPI_*` | API server configuration |
| `DASH_*` | Dashboard application settings |
| `CELERY_*` | Worker concurrency and queues |
| `SECRET_KEY` | Application secret for sessions |

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/health` | Health check |
| `GET` | `/api/v1/health/detailed` | System health and service status |
| `GET` | `/api/v1/climate/sources/available` | Discover available sources of climate data |
| `GET` | `/metrics` | Endpoint that serves Prometheus metrics |
| `POST` | `/api/v1/internal/eto/calculate` | Submit ET0 calculation request |

---

## 📈 Monitoring & Testing

- **Coverage:** 86.5% line coverage across 9,609 statements (79.0% branch). Kalman filter module: 98.4% line coverage.

- **Testing:** ~2,800 test functions (pytest, pytest‑asyncio, mock objects).

- **Prometheus + Grafana:** API metrics, response times, cache hit rates.

- **Flower:** Celery task monitoring (queue depth, worker status).

- **Loguru:** Structured logging with rotation.
  
---

## 🧪 Validation

The complete validation dataset and reproducibility package are available on **Zenodo**:

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.17791397.svg)](https://doi.org/10.5281/zenodo.17791397)

**EVAonline: An open-source web platform for global reference evapotranspiration estimation via multi-source data fusion** — Validation Dataset
*Latest version: **v1.0.2**, published **3 August 2026**. Version DOI: [10.5281/zenodo.21781466](https://doi.org/10.5281/zenodo.21781466) · Concept DOI (all versions): [10.5281/zenodo.17791397](https://doi.org/10.5281/zenodo.17791397).*

This independent validation package contains 186,286 daily observations from 17 Brazilian cities (16 in the MATOPIBA region + Piracicaba/SP) spanning the 1991–2020 climate normal period. It includes:

- **Reference data:** BR‑DWGD (Xavier et al., 0.1° resolution, 3,625+ stations)
- **Source comparisons:** NASA POWER, Open‑Meteo Archive, and EVAonline two‑stage fusion
- **Validation scripts** and statistical analyses
- **Reproducible Jupyter notebooks** for full pipeline replication

---

## 📚 References

### Cite this work

If you use EVAonline, please cite the article and the dataset:

> Soares, A.S.M.C., Ribeiro, V.P., Duarte, S.N., Balestieri, J.A.P., Padovani, C.R., Bordignon, Á.J.Z., Maciel, C.D., & Marques, P.A.A. (2026). EVAonline: An open-source web platform for global reference evapotranspiration estimation via multi-source data fusion. *Environmental Modelling & Software*, 204, 107113. https://doi.org/10.1016/j.envsoft.2026.107113

> Soares, A.S.M.C., Ribeiro, V.P., Duarte, S.N., Balestieri, J.A.P., Padovani, C.R., Bordignon, Á.J.Z., Maciel, C.D., & Marques, P.A.A. (2026). *EVAonline: An open-source web platform for global reference evapotranspiration estimation via multi-source data fusion* (Version 1.0.2) [Data set]. Zenodo. https://doi.org/10.5281/zenodo.17791397

*The DOI `10.5281/zenodo.17791397` is the concept DOI and always resolves to the latest version; the current release is v1.0.2 (`10.5281/zenodo.21781466`).*

### Data sources

Data-source citations follow each provider's official referencing/licensing page.

- **Xavier BR‑DWGD** (reference): Xavier, A.C., Scanlon, B.R., King, C.W., & Alves, A.I. (2022). New improved Brazilian daily weather gridded data (1961–2020). *International Journal of Climatology*, 42(16), 8390–8404. https://doi.org/10.1002/joc.7731
- **NASA POWER** (MERRA‑2 + CERES): NASA Langley Research Center POWER Project, Daily API (data version v10.2.1), accessed 2025/11/20. https://power.larc.nasa.gov/ — Underlying reanalysis: Gelaro, R., et al. (2017). The Modern‑Era Retrospective Analysis for Research and Applications, Version 2 (MERRA‑2). *Journal of Climate*, 30(14), 5419–5454. https://doi.org/10.1175/JCLI-D-16-0758.1
- **Open‑Meteo** (ERA5‑Land): Zippenfenig, P. (2023). Open‑Meteo.com Weather API. Zenodo. https://doi.org/10.5281/zenodo.7970649 (CC BY 4.0) — Underlying reanalysis: Muñoz‑Sabater, J., et al. (2021). ERA5‑Land: a state‑of‑the‑art global reanalysis dataset for land applications. *Earth System Science Data*, 13(9), 4349–4383. https://doi.org/10.5194/essd-13-4349-2021; Hersbach, H., et al. (2020). The ERA5 global reanalysis. *QJRMS*, 146(730), 1999–2049. https://doi.org/10.1002/qj.3803
- **MET Norway**: Locationforecast API. https://api.met.no/ — Licensed under NLOD and CC BY 4.0 ("Based on data from MET Norway").
- **NWS / NOAA**: National Weather Service API. https://www.weather.gov/documentation/services-web-api — Public domain (U.S. Government work).
- **Elevation**: Open Topo Data API (Nisbet, 2019, https://www.opentopodata.org/) over SRTM (Farr, T.G., et al., 2007. *Reviews of Geophysics*, 45, RG2004. https://doi.org/10.1029/2005RG000183) and ASTER GDEM v3 (NASA/METI, 2019. https://doi.org/10.5067/ASTER/ASTGTM.003).

### Data attribution required by providers

Following each source's official referencing/licensing page:

- **NASA POWER** ([referencing guide](https://power.larc.nasa.gov/docs/referencing/)) — include **both** references:
  - **POWER's Reference:** "The data was obtained from National Aeronautics and Space Administration (NASA) Langley Research Center's Prediction Of Worldwide Energy Resources (POWER) project funded through the NASA Earth Science Division."
  - **POWER's Data Reference:** "The data was obtained from the POWER Project's Daily API (data version v10.2.1) on 2025/11/20."
  - Data under CC BY 4.0.
- **Open‑Meteo** ([licence](https://open-meteo.com/en/licence)): cite the API software as Zippenfenig (2023), doi:10.5281/zenodo.7970649 (CC BY 4.0); underlying data from Copernicus C3S ERA5‑Land (CC BY 4.0).
- **MET Norway** ([licensing](https://www.met.no/en/free-meteorological-data/Licensing-and-crediting)): licensed under NLOD and CC BY 4.0; credit "Based on data from MET Norway".
- **NWS / NOAA** ([disclaimer](https://www.weather.gov/disclaimer)): information produced by the U.S. National Weather Service is in the public domain (U.S. Government work).
- **Elevation:** point queries served by the Open Topo Data API (Nisbet, 2019) over the SRTM (Farr et al., 2007) and ASTER GDEM v3 (NASA/METI, 2019) digital elevation models (~30 m).
- **Xavier BR‑DWGD:** Brazilian daily weather gridded product; cite Xavier et al. (2022).

### Methods & metrics

- Allen, R.G., Pereira, L.S., Raes, D., & Smith, M. (1998). Crop evapotranspiration — Guidelines for computing crop water requirements. *FAO Irrigation and Drainage Paper 56*. FAO, Rome.
- Kalman, R.E. (1960). A new approach to linear filtering and prediction problems. *Journal of Basic Engineering*, 82(1), 35–45. https://doi.org/10.1115/1.3662552
- Gupta, H.V., Kling, H., Yilmaz, K.K., & Martinez, G.F. (2009). Decomposition of the mean squared error and NSE performance criteria. *Journal of Hydrology*, 377(1–2), 80–91. https://doi.org/10.1016/j.jhydrol.2009.08.003
- Nash, J.E., & Sutcliffe, J.V. (1970). River flow forecasting through conceptual models part I. *Journal of Hydrology*, 10(3), 282–290. https://doi.org/10.1016/0022-1694(70)90255-6
- Moriasi, D.N., et al. (2007). Model evaluation guidelines for systematic quantification of accuracy in watershed simulations. *Transactions of the ASABE*, 50(3), 885–900. https://doi.org/10.13031/2013.23153

> Full BibTeX entries are available in [`EVAonline_validation/references.bib`](EVAonline_validation/references.bib).

---

## 📄 License

This project is licensed under the **GNU Affero General Public License v3.0** (AGPL-3.0). See the [LICENSE](https://github.com/angela-cunha-soares/EVAONLINE/blob/main/LICENSE) file for details.

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/angela-cunha-soares/EVAONLINE/issues)
- **Contact**: angelasilviane@alumni.usp.br | angelassilviane@gmail.com
