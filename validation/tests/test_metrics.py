"""Unit tests for validation.metrics against known closed-form values."""

import math

import numpy as np
import pytest

from validation import metrics


def test_perfect_match():
    x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    assert metrics.kge(x, x) == pytest.approx(1.0)
    assert metrics.nse(x, x) == pytest.approx(1.0)
    assert metrics.r2(x, x) == pytest.approx(1.0)
    assert metrics.mae(x, x) == pytest.approx(0.0)
    assert metrics.rmse(x, x) == pytest.approx(0.0)
    assert metrics.pbias(x, x) == pytest.approx(0.0)


def test_rmse_mae_known():
    obs = np.array([1.0, 2.0, 3.0])
    sim = np.array([2.0, 2.0, 4.0])  # errors: +1, 0, +1
    assert metrics.mae(sim, obs) == pytest.approx(2 / 3)
    assert metrics.rmse(sim, obs) == pytest.approx(math.sqrt(2 / 3))
    assert metrics.bias(sim, obs) == pytest.approx(2 / 3)


def test_pbias_sign_is_overestimation_positive():
    obs = np.array([10.0, 10.0, 10.0])
    sim = np.array([11.0, 11.0, 11.0])  # +10%
    assert metrics.pbias(sim, obs) == pytest.approx(10.0)


def test_nse_zero_for_mean_predictor():
    obs = np.array([1.0, 2.0, 3.0, 4.0])
    sim = np.full_like(obs, obs.mean())  # predicting the mean -> NSE = 0
    assert metrics.nse(sim, obs) == pytest.approx(0.0)


def test_align_drops_nan_pairs():
    sim = np.array([1.0, np.nan, 3.0, 4.0])
    obs = np.array([1.0, 2.0, np.nan, 4.0])
    s, o = metrics.align(sim, obs)  # only indices 0 and 3 survive
    assert s.tolist() == [1.0, 4.0]
    assert o.tolist() == [1.0, 4.0]


def test_align_rejects_too_few_points():
    with pytest.raises(ValueError):
        metrics.align([1.0], [1.0])


def test_length_mismatch_raises():
    with pytest.raises(ValueError):
        metrics.align([1.0, 2.0], [1.0])
