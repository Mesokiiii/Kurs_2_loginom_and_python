"""Рыночная сегментация и расчет перцентиля цены."""

from typing import Tuple, List
import numpy as np


def calculate_percentile_and_category(
    predicted_price: float,
    market_prices: List[float],
) -> Tuple[float, str]:
    """Определение процентиля цены относительно рынка и категории автомобиля."""
    if market_prices:
        percentile = float(np.mean(np.array(market_prices) <= predicted_price) * 100.0)
    else:
        percentile = 50.0

    if percentile < 25.0:
        category = "Бюджетный сегмент"
    elif percentile < 65.0:
        category = "Средний класс (Mass-Market)"
    elif percentile < 90.0:
        category = "Бизнес / Премиум класс"
    else:
        category = "Люксовый сегмент (Luxury)"

    return percentile, category


def compare_to_market(predicted_price: float, market_prices: List[float]) -> str:
    """Сравнение прогнозной цены со средней стоимостью на рынке."""
    avg_price = float(np.mean(market_prices)) if market_prices else 13277.0
    diff_pct = ((predicted_price - avg_price) / avg_price) * 100.0
    if abs(diff_pct) < 3.0:
        return f"Около среднего по рынку (${avg_price:,.0f})"
    elif diff_pct > 0:
        return f"Выше среднего (${avg_price:,.0f}) на +{diff_pct:.1f}%"
    else:
        return f"Ниже среднего (${avg_price:,.0f}) на {diff_pct:.1f}%"
