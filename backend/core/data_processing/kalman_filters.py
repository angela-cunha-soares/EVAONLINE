# backend/core/data_processing/kalman_filters.py
# Apenas os filtros Kalman — vetorizados e reutilizáveis
# No momento, aplicado somente em precipitação e ETo final calculada

import numpy as np
import pandas as pd
from typing import Dict, Optional


class AdaptiveKalmanFilter:
    def __init__(
        self,
        normal: float = 5.0,
        std: float = 1.0,
        p01: Optional[float] = None,
        p99: Optional[float] = None,
    ):
        self.normal = float(normal)
        self.std = max(float(std), 0.4)
        self.p01 = p01 if p01 is not None else normal - 3.5 * self.std
        self.p99 = p99 if p99 is not None else normal + 3.5 * self.std
        self.R_base = 0.55**2
        self.Q = self.std**2 * 0.08
        self.last_error = 0.0
        self.estimate = normal
        self.error = self.std**2

    def update(self, z: float) -> float:
        if np.isnan(z):
            return round(self.estimate, 3)

        if z < self.p01 * 0.8 or z > self.p99 * 1.25:
            R = self.R_base * 500
        elif z < self.p01 or z > self.p99:
            R = self.R_base * 50
        else:
            R = self.R_base

        current_error = abs(z - self.estimate)
        if current_error > self.last_error * 1.5:
            self.Q = min(self.Q * 1.8, self.std**2 * 0.5)
        self.last_error = current_error

        priori = self.estimate
        priori_err = self.error + self.Q
        K = priori_err / (priori_err + R)
        self.estimate = priori + K * (z - priori)
        self.error = (1 - K) * priori_err
        return round(self.estimate, 3)

    def update_batch(self, values: np.ndarray) -> np.ndarray:
        result = np.full_like(values, np.nan)
        for i, v in enumerate(values):
            if not np.isnan(v):
                result[i] = self.update(v)
        return result


class SimpleKalmanFilter:
    def __init__(self, initial_value: float = 5.0):
        self.estimate = initial_value
        self.error = 1.0
        self.Q = 0.05
        self.R = 0.8

    def update(self, z: float) -> float:
        if np.isnan(z):
            return round(self.estimate, 3)
        priori = self.estimate
        priori_err = self.error + self.Q
        K = priori_err / (priori_err + self.R)
        self.estimate = priori + K * (z - priori)
        self.error = (1 - K) * priori_err
        return round(self.estimate, 3)

    def update_batch(self, values: np.ndarray) -> np.ndarray:
        result = np.full_like(values, np.nan)
        for i, v in enumerate(values):
            if not np.isnan(v):
                result[i] = self.update(v)
        return result


class KalmanApplier:
    @staticmethod
    def apply_precipitation_filter(
        df: pd.DataFrame, ref: Optional[Dict] = None
    ) -> pd.DataFrame:
        """
        Apply Kalman filter to precipitation using sequential chronological
        processing with monthly reset (matching validated pipeline).

        Processes data in date order. Resets filter at each month boundary,
        preserving Kalman state within the same month.
        """
        if "PRECTOTCORR" not in df.columns:
            return df
        if ref:
            dates = pd.to_datetime(df["date"])
            # Ensure chronological order for sequential processing
            sort_idx = dates.argsort()
            precip = df["PRECTOTCORR"].values
            months = dates.dt.month.values

            result = np.full(len(df), np.nan)
            current_month = None
            kalman = None

            for idx in sort_idx:
                m = months[idx]
                if current_month != m:
                    # Reset filter at month boundary
                    kalman = AdaptiveKalmanFilter(
                        normal=ref["precip_normals"].get(m, 100.0),
                        std=ref["precip_stds"].get(m, 10.0),
                        p01=ref["precip_p01"].get(m),
                        p99=ref["precip_p99"].get(m),
                    )
                    current_month = m
                if not np.isnan(precip[idx]):
                    result[idx] = kalman.update(precip[idx])

            df["PRECTOTCORR"] = np.round(result, 3)
        else:
            df["PRECTOTCORR"] = df["PRECTOTCORR"].clip(0, 1800).round(3)
        return df

    @staticmethod
    def apply_eto_filter(
        df: pd.DataFrame, ref: Optional[Dict] = None, lat: float = None
    ) -> pd.DataFrame:
        """
        Apply Kalman filter to ETo using validated 3-step approach:
        1. Calculate monthly mean bias (observed - normal)
        2. Subtract bias from each observation
        3. Apply CONTINUOUS Kalman across entire series (no monthly reset)

        This matches the validated pipeline that achieved KGE=0.814.
        """
        if "et0_mm" not in df.columns:
            return df

        dates = pd.to_datetime(df["date"])
        months = dates.dt.month

        if ref:
            # STEP 1: Monthly bias calculation
            monthly_bias = {}
            for month in range(1, 13):
                mask = months == month
                if mask.sum() > 0:
                    normal = ref["eto_normals"].get(month, 5.0)
                    observed_mean = df.loc[mask, "et0_mm"].mean()
                    monthly_bias[month] = observed_mean - normal
                else:
                    monthly_bias[month] = 0.0

            # STEP 2: Bias correction
            bias_corrected = df["et0_mm"].copy()
            for i in range(len(df)):
                if pd.notna(df.iloc[i]["et0_mm"]):
                    m = months.iloc[i]
                    bias_corrected.iloc[i] = (
                        df.iloc[i]["et0_mm"] - monthly_bias.get(m, 0.0)
                    )

            # STEP 3: Continuous Kalman (no monthly reset)
            # Initialize with annual mean of normals
            annual_normal = float(np.mean(list(ref["eto_normals"].values())))
            annual_std = float(np.mean(list(ref["eto_stds"].values())))

            kalman = AdaptiveKalmanFilter(
                normal=annual_normal,
                std=annual_std,
                p01=None,
                p99=None,
            )

            result = np.full(len(df), np.nan)
            anomaly = np.full(len(df), np.nan)

            # Apply sequentially (maintains state between observations)
            for i in range(len(df)):
                if pd.notna(bias_corrected.iloc[i]):
                    # Update p01/p99 limits dynamically by month
                    m = months.iloc[i]
                    kalman.p01 = ref["eto_p01"].get(m, 0)
                    kalman.p99 = ref["eto_p99"].get(m, 10)
                    result[i] = kalman.update(bias_corrected.iloc[i])
                    anomaly[i] = result[i] - ref["eto_normals"].get(m, 5.0)

            df["eto_final"] = np.round(result, 3)
            df["anomaly_eto_mm"] = np.round(anomaly, 3)
        else:
            kalman = SimpleKalmanFilter(initial_value=5.0)
            result = kalman.update_batch(df["et0_mm"].values)
            df["eto_final"] = np.round(result, 3)
            df["anomaly_eto_mm"] = np.nan

        df["eto_evaonline"] = df["eto_final"]
        return df
