"""
Performance Tests - ETO Calculation

Benchmarks the FAO-56 Penman-Monteith calculation engine.
Ensures single-day and batch (90-day) calculations meet latency targets.

Targets (Article Table 5):
 - Single-day ETo:  < 5 ms
 - 30-day batch:    < 100 ms
 - 90-day batch:    < 300 ms

Reference: Article Section 4 (Performance evaluation)
"""

import pytest
import time
import numpy as np

from backend.core.eto_calculation.eto_services import EToCalculationService


@pytest.mark.performance
class TestEToCalculationPerformance:
    """Benchmarks for FAO-56 PM calculation."""

    @pytest.fixture
    def service(self):
        return EToCalculationService()

    @pytest.fixture
    def single_day_measurements(self):
        """Complete measurement set for one day in Jaú, SP (NASA-style keys)."""
        return {
            "T2M_MAX": 32.5,
            "T2M_MIN": 18.2,
            "T2M": 25.4,
            "RH2M": 65.0,
            "WS2M": 2.5,
            "ALLSKY_SFC_SW_DWN": 22.5,
            "date": "2023-06-15",
            "latitude": -22.2926,
            "longitude": -48.5841,
            "elevation_m": 580,
        }

    def test_single_day_under_5ms(self, service, single_day_measurements):
        """Single-day FAO-56 PM must complete in < 5 ms."""
        # Warm up
        for _ in range(10):
            service.calculate_et0(single_day_measurements)

        # Benchmark
        times = []
        for _ in range(100):
            start = time.perf_counter()
            result = service.calculate_et0(single_day_measurements)
            elapsed = (time.perf_counter() - start) * 1000  # ms
            times.append(elapsed)

        p95 = np.percentile(times, 95)
        assert p95 < 5.0, f"Single-day ETo p95={p95:.2f}ms exceeds 5ms target"
        assert result is not None

    def test_30_day_batch_under_100ms(self, service, single_day_measurements):
        """30-day batch must complete in < 100 ms."""
        days = []
        for d in range(30):
            m = single_day_measurements.copy()
            m["date"] = f"2023-06-{1+d:02d}" if d < 30 else f"2023-07-{d-29:02d}"
            days.append(m)

        # Warm up
        for m in days[:5]:
            service.calculate_et0(m)

        start = time.perf_counter()
        results = [service.calculate_et0(m) for m in days]
        elapsed = (time.perf_counter() - start) * 1000

        assert elapsed < 100.0, f"30-day batch {elapsed:.1f}ms exceeds 100ms"
        assert len(results) == 30

    def test_90_day_batch_under_300ms(self, service, single_day_measurements):
        """90-day batch must complete in < 300 ms."""
        days = []
        for d in range(90):
            m = single_day_measurements.copy()
            m["date"] = f"2023-04-{1+d:02d}" if d < 30 else f"2023-06-{d:02d}"
            days.append(m)

        start = time.perf_counter()
        results = [service.calculate_et0(m) for m in days]
        elapsed = (time.perf_counter() - start) * 1000

        assert elapsed < 300.0, f"90-day batch {elapsed:.1f}ms exceeds 300ms"
        assert len(results) == 90

    def test_eto_values_physically_valid(self, service, single_day_measurements):
        """ETo output must be within 0–15 mm/day (physical bounds)."""
        result = service.calculate_et0(single_day_measurements)
        eto = result.get("et0_mm_day", None)

        assert eto is not None, "calculate_et0 must return et0_mm_day"
        assert 0.0 <= eto <= 15.0, f"ETo={eto} outside [0, 15]"
