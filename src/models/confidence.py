"""Оценка неопределенности, доверительного интервала и вероятности цены."""

import math
from typing import Tuple, Dict, Any
import numpy as np


def calculate_confidence_interval(
    model: Any,
    x_transformed: np.ndarray,
    predicted_price: float,
    model_key: str,
    metrics_data: Dict[str, Any],
) -> Tuple[float, float]:
    """Расчет 95% доверительного интервала прогноза (дисперсия деревьев или СКО остатков)."""
    std_err = 0.0

    if hasattr(model, "estimators_"):
        tree_preds = np.array([t.predict(x_transformed)[0] for t in model.estimators_])
        std_err = float(np.std(tree_preds))
    else:
        model_metrics = metrics_data.get(model_key, {})
        std_err = float(model_metrics.get("residual_std", 2000.0))

    if std_err <= 0:
        std_err = predicted_price * 0.12

    margin = 1.96 * std_err
    ci_lower = max(2000.0, predicted_price - margin)
    ci_upper = predicted_price + margin
    return ci_lower, ci_upper


def calculate_price_probability(
    model: Any,
    x_transformed: np.ndarray,
    predicted_price: float,
    model_key: str,
    metrics_data: Dict[str, Any],
    tolerance: float = 0.15,
) -> float:
    """Вероятность попадания реальной цены в диапазон +/-15% от прогноза (в %)."""
    band = max(500.0, predicted_price * tolerance)

    if hasattr(model, "estimators_"):
        tree_preds = np.array([t.predict(x_transformed)[0] for t in model.estimators_])
        prob = float(np.mean(np.abs(tree_preds - predicted_price) <= band) * 100.0)
    else:
        model_metrics = metrics_data.get(model_key, {})
        std_err = float(model_metrics.get("residual_std", 2000.0))
        if std_err <= 0:
            std_err = predicted_price * 0.12
        prob = math.erf(band / (std_err * math.sqrt(2.0))) * 100.0

    return round(min(99.0, max(5.0, prob)), 1)


def describe_price_probability(
    prob: float,
    price_rub: float,
    tolerance: float = 0.15,
) -> Dict[str, Any]:
    """Возвращает подробную расшифровку вероятности цены, уровня надёжности и рублёвого коридора."""
    if prob >= 80.0:
        level = "Высокая надёжность (80–99%)"
    elif prob >= 60.0:
        level = "Средняя надёжность (60–79%)"
    else:
        level = "Низкая надёжность (5–59%)"

    return {
        "level": level,
        "band_low_rub": round(price_rub * (1.0 - tolerance), 0),
        "band_high_rub": round(price_rub * (1.0 + tolerance), 0),
        "subject": "Вероятность попадания реальной рыночной цены в коридор ±15% от прогноза модели",
        "valid_range": "5% – 99% (с ограничителем экстремальных значений)",
    }
