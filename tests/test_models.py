"""Unit tests for ML models inference, prediction bounds, confidence intervals, and metrics.
"""

import pytest
import numpy as np

from src.models.model_service import ModelService, PredictionResult
from src.config import CAR_PRESETS, MODEL_NAMES, USD_TO_RUB_RATE


@pytest.fixture(scope="module")
def model_service():
    """Initializes ModelService instance for test execution."""
    return ModelService()


def test_service_available_models(model_service):
    """Verifies that all 4 required ML models are registered."""
    available = model_service.get_available_models()
    assert len(available) == 4
    for model_name in MODEL_NAMES:
        assert model_name in available


def test_service_metrics_summary(model_service):
    """Verifies that model quality metrics are calculated and accessible."""
    metrics = model_service.get_metrics_summary()
    assert "random_forest" in metrics
    assert "linear_regression" in metrics
    assert "neural_network" in metrics
    assert "knn" in metrics

    for key, data in metrics.items():
        assert "test" in data
        assert "r2" in data["test"]
        assert "mae" in data["test"]
        assert "rmse" in data["test"]
        assert data["test"]["r2"] > 0.70, f"R2 too low for {key}"


@pytest.mark.parametrize("model_key", ["random_forest", "linear_regression", "neural_network", "knn"])
def test_prediction_for_all_models(model_service, model_key):
    """Tests prediction execution across all 4 machine learning models."""
    sample_features = {
        "brand": "toyota",
        "carbody": "sedan",
        "fueltype": "gas",
        "aspiration": "std",
        "drivewheel": "fwd",
        "horsepower": 105.0,
        "enginesize": 120.0,
        "curbweight": 2400.0,
        "citympg": 26.0,
        "highwaympg": 32.0,
    }

    result = model_service.predict(sample_features, model_selection=model_key)

    assert isinstance(result, PredictionResult)
    assert 2000.0 <= result.price_usd <= 50000.0
    assert result.price_rub == pytest.approx(result.price_usd * USD_TO_RUB_RATE, rel=1e-3)
    assert result.ci_lower_usd <= result.price_usd <= result.ci_upper_usd
    assert 0.0 <= result.market_percentile <= 100.0
    assert result.market_category in [
        "Бюджетный сегмент",
        "Средний класс (Mass-Market)",
        "Бизнес / Премиум класс",
        "Люксовый сегмент (Luxury)",
    ]


def test_presets_relative_ordering(model_service):
    """Verifies logical ordering: Budget Hatchback < Executive Sedan < Sports Coupe."""
    p_budget = CAR_PRESETS["Бюджетный хэтчбек (Toyota)"]
    p_sedan = CAR_PRESETS["Бизнес-седан (Audi / BMW)"]
    p_sport = CAR_PRESETS["Спорткар / Купе (Porsche)"]

    res_budget = model_service.predict(p_budget, "random_forest")
    res_sedan = model_service.predict(p_sedan, "random_forest")
    res_sport = model_service.predict(p_sport, "random_forest")

    assert res_budget.price_usd < res_sedan.price_usd < res_sport.price_usd
    assert res_budget.market_percentile < res_sedan.market_percentile < res_sport.market_percentile


def test_model_service_fallback(model_service):
    """Verifies that an unknown model name falls back gracefully without raising an exception."""
    sample_features = CAR_PRESETS["Бюджетный хэтчбек (Toyota)"]
    res = model_service.predict(sample_features, model_selection="non_existent_algorithm")
    assert isinstance(res, PredictionResult)
    assert res.price_usd > 0
