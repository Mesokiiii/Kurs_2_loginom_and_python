"""Пакет моделей машинного обучения и сервиса прогнозирования цен."""

from src.models.metrics import compute_metrics
from src.models.factories import create_regressors
from src.models.confidence import (
    calculate_confidence_interval,
    calculate_price_probability,
    describe_price_probability,
)
from src.models.market_segment import calculate_percentile_and_category, compare_to_market
from src.models.service import ModelService, PredictionResult
from src.models.train import train_and_evaluate_all

__all__ = [
    "compute_metrics",
    "create_regressors",
    "calculate_confidence_interval",
    "calculate_price_probability",
    "describe_price_probability",
    "calculate_percentile_and_category",
    "compare_to_market",
    "ModelService",
    "PredictionResult",
    "train_and_evaluate_all",
]
