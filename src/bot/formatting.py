"""Форматирование текстовых сообщений Telegram-бота."""

from typing import Any, Dict, List, Optional

from src.config import CAR_PRESETS, MODEL_NAMES
from src.models.service import ModelService, PredictionResult


def format_prediction(
    res: PredictionResult,
    features: Dict[str, Any],
    title: Optional[str] = None,
) -> str:
    """Формирует карточку результата прогноза с ценой и вероятностью."""
    header = f"<b>{title}</b>\n\n" if title else "<b>Результат прогноза</b>\n\n"
    brand = str(features.get("brand", "")).capitalize()
    body = str(features.get("carbody", "")).capitalize()
    hp = float(features.get("horsepower", 0))
    eng = float(features.get("enginesize", 0))
    weight = float(features.get("curbweight", 0))

    return (
        f"{header}"
        f"Цена: <b>${res.price_usd:,.0f}</b> (~{res.price_rub:,.0f} ₽)\n"
        f"Вероятность цены (±15%): <b>{res.price_probability:.1f}%</b>\n"
        f"95% интервал: ${res.ci_lower_usd:,.0f} – ${res.ci_upper_usd:,.0f}\n"
        f"Сегмент: {res.market_category} (дороже {res.market_percentile:.1f}%)\n"
        f"Рынок: {res.comparison_to_average}\n"
        f"Модель: {res.model_name}\n\n"
        f"Параметры: {brand} ({body}), {hp:.0f} л.с., {eng:.0f} cu in, {weight:.0f} lbs"
    )


def format_presets_overview(service: ModelService) -> str:
    """Формирует список пресетов с рассчитанной ценой и вероятностью."""
    lines = ["<b>Готовые пресеты автомобилей</b>\n"]
    for name, data in CAR_PRESETS.items():
        res = service.predict(data, model_selection=MODEL_NAMES[0])
        lines.append(
            f"• <b>{name}</b>\n"
            f"  Цена: <b>${res.price_usd:,.0f}</b> ({res.price_rub:,.0f} ₽) | "
            f"Вероятность: <b>{res.price_probability:.1f}%</b>"
        )
    lines.append("\nВыберите пресет ниже для подробного расчёта:")
    return "\n".join(lines)


def format_history(records: List[Dict[str, Any]]) -> str:
    """Формирует список последних расчётов пользователя."""
    if not records:
        return "История расчётов пуста. Нажмите «Рассчитать авто» или выберите пресет."

    lines = ["<b>Ваши последние расчёты</b>\n"]
    for rec in records:
        ts = str(rec.get("timestamp", ""))[:16].replace("T", " ")
        brand = str(rec.get("brand", "")).capitalize()
        body = str(rec.get("carbody", "")).capitalize()
        price_usd = float(rec.get("predicted_price_usd", 0))
        model_name = rec.get("model_name", "")
        lines.append(f"• {ts} — {brand} ({body}): <b>${price_usd:,.0f}</b> [{model_name}]")
    return "\n".join(lines)
