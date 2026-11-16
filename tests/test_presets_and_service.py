"""Unit tests for car presets and prediction service logic."""

import pytest
import numpy as np
from src.config import CAR_PRESETS
from src.models.metrics import compute_metrics
from src.models.market_segment import calculate_percentile_and_category, compare_to_market


def test_presets_structure():
    """Verifies that presets dictionary has expected cars and structure."""
    assert len(CAR_PRESETS) >= 4
    for name, p in CAR_PRESETS.items():
        assert "brand" in p
        assert "carbody" in p
        assert "horsepower" in p
        assert "enginesize" in p
        assert "curbweight" in p


def test_presets_value_ranges():
    """Verifies that preset physical values are within valid engineering limits."""
    for name, p in CAR_PRESETS.items():
        assert 40 <= p["horsepower"] <= 400
        assert 50 <= p["enginesize"] <= 450
        assert 1200 <= p["curbweight"] <= 5000


def test_compute_metrics_perfect():
    """Verifies metrics with zero-error synthetic data."""
    y = np.array([10000.0, 20000.0, 30000.0])
    metrics = compute_metrics(y, y)
    assert metrics["r2"] == 1.0
    assert metrics["mae"] == 0.0
    assert metrics["rmse"] == 0.0
    assert metrics["mape"] == 0.0


def test_compute_metrics_deviation():
    """Verifies evaluator metric calculations under intentional error."""
    y_true = np.array([10000.0, 20000.0])
    y_pred = np.array([11000.0, 19000.0])
    metrics = compute_metrics(y_true, y_pred)
    assert metrics["mae"] == 1000.0
    assert metrics["rmse"] == 1000.0
    assert metrics["mape"] > 0.0


def test_presets_keys_naming():
    """Checks preset names contain expected car makes."""
    preset_names = list(CAR_PRESETS.keys())
    assert any("Toyota" in name for name in preset_names)
    assert any("BMW" in name for name in preset_names)
    assert any("Porsche" in name for name in preset_names)


def test_market_segment_classification():
    """Tests categorization into budget, middle, premium, luxury."""
    market = [5000.0, 10000.0, 15000.0, 20000.0, 30000.0, 45000.0]
    p_bud, cat_bud = calculate_percentile_and_category(4000.0, market)
    assert "Бюджет" in cat_bud
    p_lux, cat_lux = calculate_percentile_and_category(50000.0, market)
    assert "Люкс" in cat_lux

    comp = compare_to_market(20000.0, market)
    assert "Выше" in comp or "Ниже" in comp or "Около" in comp
