# backend/core/data_processing/climate_ensemble.py
# Orquestrador final

import pandas as pd
from loguru import logger
from typing import Optional

from .historical_loader import HistoricalDataLoader
from .kalman_filters import KalmanApplier
from .climate_fusion import (
    ClimateFusion,
)


class ClimateKalmanEnsemble:
    def __init__(self):
        self.loader = HistoricalDataLoader()
        self.fusion = ClimateFusion()
        self.kalman = KalmanApplier()

    def process(
        self,
        df_multi_source: pd.DataFrame,
        lat: float,
        lon: float,
        mode: Optional[str] = None,
    ) -> pd.DataFrame:
        if df_multi_source.empty:
            logger.warning("DataFrame vazio recebido")
            return pd.DataFrame()

        # 1. Fusão das variáveis climáticas
        fused_df = self.fusion.fuse_multi_source(df_multi_source, lat, lon, mode=mode)

        # 2. Busca referência local
        has_ref, ref = self.loader.get_reference_for_location(lat, lon)

        # 3. Aplicar Kalman na precipitação
        # (ETo Kalman é aplicado DEPOIS do cálculo de ETo, em eto_services)
        df = self.kalman.apply_precipitation_filter(
            fused_df, ref if has_ref else None
        )

        # 4. Modo final
        df["fusion_mode"] = "high_precision" if has_ref else "global_fallback"

        logger.success(
            f"Fusão + Kalman completa: {len(df)} dias | Modo: {df['fusion_mode'].iloc[0]}"
        )
        return df
