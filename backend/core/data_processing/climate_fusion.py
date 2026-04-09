# backend/core/data_processing/climate_fusion.py
# Fusão pura de dados climáticos — sem Kalman, sem loader de referência

import numpy as np
import pandas as pd
from loguru import logger
from typing import Dict

from backend.core.data_processing.climate_limits import get_fusion_limits
from backend.core.utils import detect_geographic_region


class ClimateFusion:
    """
    Responsável apenas pela fusão inteligente de múltiplas fontes climáticas.
    Não aplica Kalman. Não busca referência local.
    """

    # Source classification
    HIST_SOURCES = {"nasa_power", "openmeteo_archive"}
    PRIMARY_SOURCES = {"nasa_power", "openmeteo_archive"}  # High-quality reanalysis
    FALLBACK_SOURCES = {"openmeteo_forecast"}  # Gap-filler for historical+recent mode
    # All sources valid in historical mode (primary + gap-filler)
    HISTORICAL_ALL_SOURCES = {"nasa_power", "openmeteo_archive", "openmeteo_forecast"}

    # Per-variable NASA POWER weights for historical AND recent mode (2-source fusion).
    # OpenMeteo receives 1 - w. Calibrated against BR-DWGD (17 sites).
    HIST_WEIGHTS = {
        "T2M_MAX": 0.58,           # NASA slight advantage in extremes
        "T2M_MIN": 0.52,           # Near-equal performance
        "T2M": 0.60,               # NASA MERRA-2 advantage
        "RH2M": 0.35,              # ERA5 humidity superior
        "WS2M": 0.20,              # ERA5 wind more accurate
        "ALLSKY_SFC_SW_DWN": 0.92, # CERES satellite radiation dominant
        "PRECTOTCORR": 0.50,       # Equal reliability; Kalman handles QC
    }

    # Variables to fuse (also determines iteration order)
    WEIGHTS = {
        "T2M_MAX": 0.58,
        "T2M_MIN": 0.52,
        "T2M": 0.60,
        "RH2M": 0.35,
        "WS2M": 0.20,
        "ALLSKY_SFC_SW_DWN": 0.92,
        "PRECTOTCORR": 0.50,
    }

    GLOBAL_LIMITS = get_fusion_limits()

    def __init__(self):
        self.quality_metrics = {}
        self.source_health = {}

    def _validate_climate_data(self, df: pd.DataFrame, source_name: str):
        for var, (min_val, max_val) in self.GLOBAL_LIMITS.items():
            if var in df.columns:
                invalid = (df[var] < min_val) | (df[var] > max_val)
                if invalid.any():
                    logger.warning(
                        f"{source_name}: {invalid.sum()} valores de {var} fora dos limites físicos"
                    )

    def _track_data_quality(self, df: pd.DataFrame, source_name: str):
        if source_name not in self.quality_metrics:
            self.quality_metrics[source_name] = {
                "total_records": 0,
                "quality_scores": {},
            }

        metrics = self.quality_metrics[source_name]
        metrics["total_records"] = len(df)

        for var in self.WEIGHTS:
            if var not in df.columns:
                continue
            completeness = df[var].notna().mean()
            outliers = 0
            if var in self.GLOBAL_LIMITS:
                min_val, max_val = self.GLOBAL_LIMITS[var]
                outliers = ((df[var] < min_val) | (df[var] > max_val)).mean()
            score = completeness * (1 - outliers)
            metrics["quality_scores"][var] = round(score * 100, 2)

    def _check_source_health(self, source_name: str) -> bool:
        if source_name not in self.quality_metrics:
            return True
        scores = self.quality_metrics[source_name]["quality_scores"]
        if not scores:
            return True
        avg_quality = np.mean(list(scores.values()))
        is_healthy = avg_quality >= 60.0
        if not is_healthy:
            logger.warning(
                f"Circuit Breaker: {source_name} degradada (qualidade: {avg_quality:.1f}%)"
            )
        return is_healthy

    def _detect_region_with_priority(self, lat: float, lon: float) -> Dict:
        region = detect_geographic_region(lat, lon)
        if region == "usa":
            return {
                "name": "USA",
                "weights": {
                    "nws_forecast": 0.50,
                    "openmeteo_forecast": 0.30,
                    "met_norway": 0.20,
                },
                "order": ["nws_forecast", "openmeteo_forecast", "met_norway"],
            }
        elif region == "nordic":
            return {
                "name": "NORDIC",
                "weights": {"met_norway": 0.80, "openmeteo_forecast": 0.20},
                "order": ["met_norway", "openmeteo_forecast"],
            }
        else:
            return {
                "name": "GLOBAL",
                "weights": {"openmeteo_forecast": 0.70, "met_norway": 0.30},
                "order": ["openmeteo_forecast", "met_norway"],
            }

    def _prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        if "source" in df.columns:
            for src in df["source"].unique():
                sub = df[df["source"] == src]
                self._validate_climate_data(sub, src)
                self._track_data_quality(sub, src)
        else:
            self._validate_climate_data(df, "unknown_source")
            self._track_data_quality(df, "unknown_source")

        if "date" not in df.columns:
            if isinstance(df.index, pd.DatetimeIndex):
                df = df.reset_index()
            else:
                logger.error("Coluna 'date' ausente e índice não é datetime")
                return df

        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")

        # Remove duplicatas: preservar todas as fontes diferentes por data,
        # deduplicar apenas quando a MESMA fonte tem a mesma data duas vezes
        # (ex: janela de arquivo e previsão sobrepostas do mesmo API).
        # NÃO remover fontes diferentes para a mesma data — a fusão depende
        # de ter openmeteo_forecast E met_norway simultaneamente por data
        # para combinar vento/radiação (OM) com temp/umidade (MET).
        if df.index.duplicated().any():
            if "source" in df.columns:
                # Manter apenas uma linha por (date, source) — fontes
                # diferentes para a mesma data são PRESERVADAS intencionalmente
                df_reset = df.reset_index()
                df_reset = df_reset.drop_duplicates(
                    subset=["date", "source"], keep="first"
                )
                df = df_reset.set_index("date")
                logger.debug(
                    f"Dedup por (date, source): {len(df)} linhas preservadas "
                    f"({df['source'].value_counts().to_dict()})"
                )
            else:
                # Sem coluna source: manter apenas primeira ocorrência por data
                df = df[~df.index.duplicated(keep="first")]

        return df

    def _interpolate_safe(self, series: pd.Series) -> pd.Series:
        interpolated = series.interpolate(
            method="linear", limit=3, limit_direction="both"
        )
        if series.name in self.GLOBAL_LIMITS:
            min_val, max_val = self.GLOBAL_LIMITS[series.name]
            interpolated = interpolated.clip(min_val, max_val)
        return interpolated

    def fuse_multi_source(
        self, df: pd.DataFrame, lat: float, lon: float,
        mode: str = None,
    ) -> pd.DataFrame:
        if df.empty:
            logger.warning("DataFrame vazio na fusão")
            return pd.DataFrame(columns=["date"] + list(self.WEIGHTS.keys()))

        df = self._prepare_data(df)
        region = self._detect_region_with_priority(lat, lon)

        # Circuit Breaker
        healthy_sources = [
            s for s in region["order"] if self._check_source_health(s)
        ]
        if not healthy_sources:
            logger.error(
                "Todas as fontes com problemas → usando fallback simples"
            )
            dates = pd.date_range(
                start=pd.Timestamp.now().date(), periods=7, freq="D"
            )
            return pd.DataFrame(
                {
                    "date": dates,
                    "T2M": 20.0,
                    "T2M_MAX": 28.0,
                    "T2M_MIN": 15.0,
                    "RH2M": 70.0,
                    "WS2M": 3.0,
                    "ALLSKY_SFC_SW_DWN": 20.0,
                    "PRECTOTCORR": 2.0,
                    "fusion_mode": "emergency_fallback",
                }
            ).set_index("date")

        weights = {s: region["weights"][s] for s in healthy_sources}
        total = sum(weights.values())
        weights = {k: v / total for k, v in weights.items()}

        # Fusão por dia
        result_rows = []
        fusion_strategy = (
            {}
        )  # Track which variables use single vs multi-source

        # Detect operational mode from parameter or source names
        all_sources = set()
        if "source" in df.columns:
            all_sources = set(df["source"].unique())

        # Explicit mode detection
        mode_normalized = (mode or "").lower().replace(" ", "_")
        is_historical = (
            "historical" in mode_normalized
            or (all_sources.issubset(self.HISTORICAL_ALL_SOURCES) and len(all_sources & self.PRIMARY_SOURCES) >= 1)
        )
        is_recent = "current" in mode_normalized or "dashboard_current" in mode_normalized

        for date, group in df.groupby(df.index):
            row = {"date": date}
            if "source" in group.columns:
                sources = {src: sub for src, sub in group.groupby("source")}
            else:
                sources = {"default": group}

            for var in self.WEIGHTS:
                values = {}
                for src, sub in sources.items():
                    if var in sub.columns and pd.notna(sub[var].iloc[0]):
                        values[src] = sub[var].iloc[0]

                if not values:
                    row[var] = np.nan
                    continue

                # Se apenas uma fonte tem a variável → usar 100% dela (single-source)
                if len(values) == 1:
                    source_name = list(values.keys())[0]
                    if var not in fusion_strategy:
                        fusion_strategy[var] = {"single": source_name}
                    row[var] = list(values.values())[0]
                    continue

                # Historical mode: adaptive per-variable per-day fusion
                # Primary sources (NASA + Archive) use HIST_WEIGHTS
                # OM Forecast is gap-filler only when primaries unavailable
                if is_historical:
                    primary_vals = {
                        s: v for s, v in values.items()
                        if s in self.PRIMARY_SOURCES
                    }
                    fallback_vals = {
                        s: v for s, v in values.items()
                        if s in self.FALLBACK_SOURCES
                    }

                    if len(primary_vals) >= 2:
                        # Both primary sources → HIST_WEIGHTS
                        if var not in fusion_strategy:
                            fusion_strategy[var] = {"hist_weighted": list(primary_vals.keys())}
                        if var == "PRECTOTCORR":
                            row[var] = np.mean(list(primary_vals.values()))
                        else:
                            w_nasa = self.HIST_WEIGHTS.get(var, 0.50)
                            weighted = 0.0
                            total_w = 0.0
                            for src, val in primary_vals.items():
                                w = w_nasa if src == "nasa_power" else (1.0 - w_nasa)
                                weighted += w * val
                                total_w += w
                            row[var] = (
                                weighted / total_w
                                if total_w > 0
                                else np.mean(list(primary_vals.values()))
                            )
                    elif len(primary_vals) == 1:
                        # One primary source → 100%
                        src_name = list(primary_vals.keys())[0]
                        if var not in fusion_strategy:
                            fusion_strategy[var] = {"hist_single_primary": src_name}
                        row[var] = list(primary_vals.values())[0]
                    elif fallback_vals:
                        # No primary → gap-fill from OM Forecast 100%
                        src_name = list(fallback_vals.keys())[0]
                        if var not in fusion_strategy:
                            fusion_strategy[var] = {"hist_gapfill": src_name}
                        row[var] = list(fallback_vals.values())[0]
                    else:
                        row[var] = list(values.values())[0]
                    continue

                # Recent mode: primary sources preferred, forecast as gap-filler
                if is_recent:
                    primary_vals = {
                        s: v for s, v in values.items()
                        if s in self.PRIMARY_SOURCES
                    }
                    if primary_vals:
                        # At least one primary source has this variable
                        if len(primary_vals) == 1:
                            # Single primary source → 100%
                            row[var] = list(primary_vals.values())[0]
                            if var not in fusion_strategy:
                                fusion_strategy[var] = {
                                    "recent_single": list(primary_vals.keys())[0]
                                }
                        else:
                            # Both primary sources → HIST_WEIGHTS
                            if var not in fusion_strategy:
                                fusion_strategy[var] = {
                                    "recent_hist": list(primary_vals.keys())
                                }
                            if var == "PRECTOTCORR":
                                row[var] = np.mean(list(primary_vals.values()))
                            else:
                                w_nasa = self.HIST_WEIGHTS.get(var, 0.50)
                                weighted = 0.0
                                total_w = 0.0
                                for src, val in primary_vals.items():
                                    w = w_nasa if src == "nasa_power" else (1.0 - w_nasa)
                                    weighted += w * val
                                    total_w += w
                                row[var] = (
                                    weighted / total_w
                                    if total_w > 0
                                    else np.mean(list(primary_vals.values()))
                                )
                    else:
                        # No primary source for this var → use forecast 100%
                        fallback_vals = {
                            s: v for s, v in values.items()
                            if s in self.FALLBACK_SOURCES
                        }
                        if fallback_vals:
                            row[var] = list(fallback_vals.values())[0]
                            if var not in fusion_strategy:
                                fusion_strategy[var] = {
                                    "recent_fallback": list(fallback_vals.keys())[0]
                                }
                        else:
                            row[var] = list(values.values())[0]
                    continue

                # Forecast mode: per-source region weights
                if var not in fusion_strategy:
                    fusion_strategy[var] = {"multi": list(values.keys())}
                weighted = 0.0
                total_w = 0.0
                for src, val in values.items():
                    w = weights.get(src, 0.1)
                    weighted += w * val
                    total_w += w
                row[var] = (
                    weighted / total_w
                    if total_w > 0
                    else list(values.values())[0]
                )

            result_rows.append(row)

        result_df = pd.DataFrame(result_rows).set_index("date")

        # Clip final e interpolação
        for col in result_df.columns:
            if col in self.GLOBAL_LIMITS:
                min_val, max_val = self.GLOBAL_LIMITS[col]
                result_df[col] = result_df[col].clip(min_val, max_val)
            result_df[col] = self._interpolate_safe(result_df[col])

        result_df = result_df.dropna(thresh=4)  # pelo menos 3 vars + date
        result_df = result_df.reset_index()

        # Determine effective mode label for logging
        if is_historical:
            mode_label = "HISTORICAL"
        elif is_recent:
            mode_label = "RECENT"
        else:
            mode_label = f"FORECAST ({region['name']})"

        # Log da estratégia de fusão por variável
        logger.info(f"🔀 Fusion strategy [{mode_label}]:")
        for var, strategy in fusion_strategy.items():
            if "single" in strategy:
                logger.info(
                    f"   {var}: 100% {strategy['single']} (single-source)"
                )
            elif "hist_weighted" in strategy:
                logger.info(
                    f"   {var}: HIST_WEIGHTS {strategy['hist_weighted']}"
                )
            elif "hist_single_primary" in strategy:
                logger.info(
                    f"   {var}: 100% {strategy['hist_single_primary']} (primary-only, partner unavailable)"
                )
            elif "hist_gapfill" in strategy:
                logger.info(
                    f"   {var}: 100% {strategy['hist_gapfill']} (gap-fill, no primary data)"
                )
            elif "recent_single" in strategy:
                logger.info(
                    f"   {var}: 100% {strategy['recent_single']} (primary-only)"
                )
            elif "recent_hist" in strategy:
                logger.info(
                    f"   {var}: HIST_WEIGHTS {strategy['recent_hist']} (primary pair)"
                )
            elif "recent_fallback" in strategy:
                logger.info(
                    f"   {var}: 100% {strategy['recent_fallback']} (gap-filler)"
                )
            elif "multi" in strategy:
                sources_str = ", ".join(
                    f"{s} ({weights.get(s, 0.1)*100:.0f}%)"
                    for s in strategy["multi"]
                )
                logger.info(f"   {var}: {sources_str} (multi-source fusion)")

        logger.success(
            f"Fusão concluída: {len(result_df)} dias | Região: {region['name']}"
        )
        return result_df
