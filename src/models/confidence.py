"""Оценка неопределенности и расчет доверительного интервала."""

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
