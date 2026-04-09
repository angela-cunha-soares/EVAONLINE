# backend/core/data_processing/historical_loader.py
# Responsável por carregar referência climática local

import json
from pathlib import Path
from typing import Dict, Optional, Tuple

import pandas as pd
from loguru import logger

from backend.core.utils import (
    detect_geographic_region,
    haversine_distance,
    is_same_hemisphere,
)


class ThreadSafeCache:
    """Cache thread-safe com LRU simples"""

    def __init__(self, max_size: int = 1000):
        from collections import OrderedDict
        import threading

        self._cache = OrderedDict()
        self._lock = threading.RLock()
        self._max_size = max_size

    def get(self, key):
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
        return None

    def set(self, key, value):
        with self._lock:
            self._cache[key] = value
            self._cache.move_to_end(key)
            if len(self._cache) > self._max_size:
                self._cache.popitem(last=False)

    def clear(self):
        with self._lock:
            self._cache.clear()


class HistoricalDataLoader:
    def __init__(self):
        base_dir = Path(__file__).resolve().parent.parent.parent.parent
        self.historical_dir = base_dir / "data" / "historical" / "cities"
        self.city_coords_path = (
            base_dir / "data" / "historical" / "info_cities.csv"
        )
        self.city_coords = self._load_city_coords()
        self._cache = ThreadSafeCache(max_size=1000)

    def _load_city_coords(self) -> Dict:
        if not self.city_coords_path.exists():
            logger.warning("info_cities.csv não encontrado")
            return {}
        try:
            df = pd.read_csv(self.city_coords_path)
            return {
                str(row["city"]): (
                    float(row["lat"]),
                    float(row["lon"]),
                    str(row.get("region", "global")),
                )
                for _, row in df.iterrows()
            }
        except Exception as e:
            logger.error(f"Erro carregando coordenadas: {e}")
            return {}

    def _read_json_with_timeout(self, file_path: Path) -> Optional[Dict]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Erro lendo {file_path.name}: {e}")
            return None

    def get_reference_for_location(
        self, lat: float, lon: float, max_dist_km: float = 200.0
    ) -> Tuple[bool, Optional[Dict]]:
        key = (round(lat, 3), round(lon, 3))

        cached = self._cache.get(key)
        if cached is not None:
            return (True, cached) if cached != "NOT_FOUND" else (False, None)

        query_region = detect_geographic_region(lat, lon)
        best_dist = float("inf")
        best_path = None
        best_city_key = None

        for json_path in self.historical_dir.glob("report_*.json"):
            city_key = json_path.stem.removeprefix("report_")
            if city_key not in self.city_coords:
                continue

            c_lat, c_lon, c_region = self.city_coords[city_key]

            # Evita usar cidades brasileiras fora do Brasil e vice-versa
            if query_region == "brasil" and c_region != "brasil":
                continue
            if query_region != "brasil" and c_region == "brasil":
                continue

            if abs(abs(lon) - abs(c_lon)) > 60:
                continue
            if not is_same_hemisphere(lat, c_lat):
                continue

            dist = haversine_distance(lat, lon, c_lat, c_lon)
            if dist < best_dist and dist <= max_dist_km:
                best_dist = dist
                best_path = json_path
                best_city_key = city_key

        if not best_path:
            self._cache.set(key, "NOT_FOUND")
            return False, None

        data = self._read_json_with_timeout(best_path)
        if not data:
            self._cache.set(key, "NOT_FOUND")
            return False, None

        monthly = data["climate_normals_all_periods"]["1991-2020"]["monthly"]
        ref = {
            "city": best_city_key,
            "distance_km": round(best_dist, 1),
            "eto_normals": {
                int(m): float(v.get("normal", 5.0)) for m, v in monthly.items()
            },
            "eto_stds": {
                int(m): max(float(v.get("daily_std", 1.0)), 0.5)
                for m, v in monthly.items()
            },
            "eto_p01": {
                int(m): float(v.get("p01", 2.0)) for m, v in monthly.items()
            },
            "eto_p99": {
                int(m): float(v.get("p99", 8.0)) for m, v in monthly.items()
            },
            "precip_normals": {
                int(m): float(v.get("precip_normal", 100.0))
                for m, v in monthly.items()
            },
            "precip_stds": {
                int(m): max(float(v.get("precip_daily_std", 10.0)), 5.0)
                for m, v in monthly.items()
            },
            "precip_p01": {
                int(m): float(v.get("precip_p01", 0.0))
                for m, v in monthly.items()
            },
            "precip_p99": {
                int(m): float(v.get("precip_p99", 450.0))
                for m, v in monthly.items()
            },
        }

        self._cache.set(key, ref)
        logger.info(f"Referência local: {ref['city']} ({best_dist:.1f} km)")
        return True, ref
