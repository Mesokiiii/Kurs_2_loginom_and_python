"""Форматирование текстовых сообщений Telegram-бота (все цены в рублях)."""

from typing import Any, Dict, List, Optional

from src.config import (
    ASPIRATION_LABELS,
    BODY_LABELS,
    CAR_PRESETS,
    DRIVE_LABELS,
    FUEL_LABELS,
    MODEL_NAMES,
    USD_TO_RUB_RATE,
    format_model_with_quality,
    format_rub,
)
from src.models.confidence import describe_price_probability
from src.models.service import ModelService, PredictionResult


def format_prediction(
    res: PredictionResult,
    features: Dict[str, Any],
    title: Optional[str] = None,
    metrics: Optional[Dict[str, Any]] = None,
) -> str:
    """Формирует карточку результата прогноза с ценой в рублях, вероятностью и версией модели."""
    header = f"<b>{title}</b>\n\n" if title else "<b>Результат прогноза</b>\n\n"
    brand = str(features.get("brand", "")).capitalize()
    body_key = str(features.get("carbody", "")).lower()
    body_ru = BODY_LABELS.get(body_key, body_key.capitalize())
    drive_key = str(features.get("drivewheel", "fwd")).lower()
    drive_ru = DRIVE_LABELS.get(drive_key, drive_key.upper())
    fuel_key = str(features.get("fueltype", "gas")).lower()
    fuel_ru = FUEL_LABELS.get(fuel_key, fuel_key)
    asp_key = str(features.get("aspiration", "std")).lower()
    asp_ru = ASPIRATION_LABELS.get(asp_key, asp_key)

    hp = float(features.get("horsepower", 0))
    eng = float(features.get("enginesize", 0))
    weight = float(features.get("curbweight", 0))

    prob_desc = describe_price_probability(res.price_probability, res.price_rub)
    band_low = res.probability_band_low_rub or prob_desc["band_low_rub"]
    band_high = res.probability_band_high_rub or prob_desc["band_high_rub"]
    prob_level = res.probability_level or prob_desc["level"]
    model_str = format_model_with_quality(res.model_key, metrics)

    warnings_block = ""
    if res.clamped_warnings:
        warnings_block = (
            "\n<b>Ограничитель параметров:</b>\n"
            + "\n".join(f"• {w}" for w in res.clamped_warnings)
            + "\n"
        )

    return (
        f"{header}"
        f"Цена: <b>{format_rub(res.price_rub)}</b>\n"
        f"Вероятность цены (±15%): <b>{res.price_probability:.1f}%</b> — {prob_level}\n"
        f"Коридор ±15%: {format_rub(band_low)} – {format_rub(band_high)}\n"
        f"95% интервал: {format_rub(res.ci_lower_rub)} – {format_rub(res.ci_upper_rub)}\n"
        f"Сегмент: {res.market_category} (дороже {res.market_percentile:.1f}% рынка)\n"
        f"Рынок: {res.comparison_to_average}\n"
        f"Модель: {model_str}\n"
        f"{warnings_block}\n"
        f"Параметры: {brand} ({body_ru}), {drive_ru}, {fuel_ru} ({asp_ru}), "
        f"{hp:.0f} л.с., {eng:.0f} куб. дюймов, {weight:.0f} фунтов"
    )


def format_presets_overview(service: ModelService) -> str:
    """Формирует список пресетов с рассчитанной ценой в рублях и вероятностью."""
    metrics = service.get_metrics_summary()
    model_str = format_model_with_quality(MODEL_NAMES[0], metrics)
    lines = [
        "<b>Готовые пресеты автомобилей</b>",
        f"<i>Модель: {model_str}</i>\n",
    ]
    for name, data in CAR_PRESETS.items():
        res = service.predict(data, model_selection=MODEL_NAMES[0])
        short_level = res.probability_level.split(" (")[0] if res.probability_level else ""
        lines.append(
            f"• <b>{name}</b>\n"
            f"  Цена: <b>{format_rub(res.price_rub)}</b> | "
            f"Вероятность: <b>{res.price_probability:.1f}%</b> ({short_level})"
        )
    lines.append("\nВыберите пресет ниже для подробного расчёта:")
    return "\n".join(lines)


def format_history(records: List[Dict[str, Any]]) -> str:
    """Формирует список последних расчётов пользователя в рублях."""
    if not records:
        return "История расчётов пуста. Нажмите «Рассчитать авто» или выберите пресет."

    lines = ["<b>Ваши последние расчёты (SQLite)</b>\n"]
    for rec in records:
        ts = str(rec.get("timestamp", ""))[:16].replace("T", " ")
        brand = str(rec.get("brand", "")).capitalize()
        body_key = str(rec.get("carbody", "")).lower()
        body_ru = BODY_LABELS.get(body_key, body_key.capitalize())
        price_rub = float(rec.get("predicted_price_rub") or 0)
        if price_rub <= 0:
            price_rub = float(rec.get("predicted_price_usd", 0)) * USD_TO_RUB_RATE
        model_name = rec.get("model_name", "")
        lines.append(f"• {ts} — {brand} ({body_ru}): <b>{format_rub(price_rub)}</b> [{model_name}]")
    return "\n".join(lines)
