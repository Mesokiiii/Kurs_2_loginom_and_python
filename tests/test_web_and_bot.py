"""Тесты для вероятности цены, ограничителя параметров, версионирования, веб-интерфейса и Telegram-бота."""

import json

from src.config import (
    BODY_LABELS,
    CAR_PRESETS,
    FEATURE_RANGES,
    METADATA_PATH,
    MODEL_NAMES,
    MODEL_VERSION,
    format_model_with_quality,
)
from src.data.validator import clamp_car_features
from src.models.confidence import describe_price_probability
from src.models.market_segment import compare_to_market
from src.models.service import ModelService
from src.bot.app import create_dispatcher
from src.bot.formatting import format_history, format_prediction, format_presets_overview
from src.bot.keyboards import (
    BTN_HELP,
    bodies_kb,
    brands_kb,
    main_menu_kb,
    models_kb,
    presets_kb,
)


def test_price_probability_for_all_models():
    service = ModelService()
    preset = CAR_PRESETS["Бюджетный хэтчбек (Toyota)"]

    results = service.predict_all_models(preset)
    assert len(results) == len(MODEL_NAMES)
    for res in results:
        assert res.price_usd > 0
        assert res.price_rub > 0
        assert 5.0 <= res.price_probability <= 99.0
        assert res.model_version == MODEL_VERSION
        assert res.probability_band_low_rub < res.price_rub < res.probability_band_high_rub
        assert res.probability_level != ""


def test_presets_have_valid_price_and_probability():
    service = ModelService()
    for name, data in CAR_PRESETS.items():
        res = service.predict(data)
        assert res.price_usd > 0, f"Нулевая цена для пресета {name}"
        assert 5.0 <= res.price_probability <= 99.0


def test_clamp_car_features_limiter():
    """Проверяет строгий ограничитель диапазонов для числовых и категориальных параметров."""
    raw = {
        "brand": "unknown_brand",
        "carbody": "spaceship",
        "horsepower": 9999.0,
        "enginesize": 10.0,
        "curbweight": 2500.0,
    }
    clamped, warnings = clamp_car_features(raw)

    assert clamped["horsepower"] == FEATURE_RANGES["horsepower"][1]
    assert clamped["enginesize"] == FEATURE_RANGES["enginesize"][0]
    assert clamped["curbweight"] == 2500.0
    assert clamped["brand"] == "toyota"
    assert clamped["carbody"] == "sedan"
    assert len(warnings) == 4

    # Проверка, что ModelService применяет ограничитель и возвращает предупреждения
    service = ModelService()
    res = service.predict(raw)
    assert res.price_rub > 0
    assert len(res.clamped_warnings) == 4

    # Корректные данные не вызывают предупреждений
    valid_clamped, valid_warnings = clamp_car_features(CAR_PRESETS["Бюджетный хэтчбек (Toyota)"])
    assert valid_warnings == []
    assert valid_clamped["horsepower"] == CAR_PRESETS["Бюджетный хэтчбек (Toyota)"]["horsepower"]


def test_format_model_with_quality():
    """Проверяет версионирование и отображение качества моделей в скобках."""
    service = ModelService()
    metrics = service.get_metrics_summary()

    rf_label = format_model_with_quality("random_forest", metrics)
    assert MODEL_VERSION in rf_label
    assert "R² = 0.96" in rf_label
    assert "ошибка 9.1%" in rf_label

    ridge_label = format_model_with_quality("Гребневая регрессия (Ridge)", metrics)
    assert MODEL_VERSION in ridge_label
    assert "R² = 0.90" in ridge_label
    assert "ошибка 16.9%" in ridge_label

    # Без переданных метрик используются дефолтные значения реестра
    knn_default = format_model_with_quality("knn")
    assert MODEL_VERSION in knn_default
    assert "R² = 0.77" in knn_default


def test_describe_price_probability():
    """Проверяет уровни надёжности и расчёт рублёвого коридора ±15%."""
    high = describe_price_probability(88.5, 1_000_000.0)
    assert "Высокая надёжность" in high["level"]
    assert high["band_low_rub"] == 850_000.0
    assert high["band_high_rub"] == 1_150_000.0
    assert "±15%" in high["subject"]
    assert "5% – 99%" in high["valid_range"]

    medium = describe_price_probability(72.0, 2_000_000.0)
    assert "Средняя надёжность" in medium["level"]

    low = describe_price_probability(41.0, 500_000.0)
    assert "Низкая надёжность" in low["level"]


def test_bot_formatting_and_keyboards_no_dollars():
    """Проверяет форматирование бота: рубли без знака '$', русские названия, кнопка Справка."""
    service = ModelService()
    metrics = service.get_metrics_summary()
    preset = CAR_PRESETS["Спорткар / Купе (Porsche)"]
    res = service.predict(preset)

    card = format_prediction(res, preset, title="Porsche", metrics=metrics)
    assert "Цена:" in card
    assert "₽" in card
    assert "$" not in card
    assert "USD" not in card
    assert "Вероятность цены" in card
    assert f"{res.price_probability:.1f}%" in card
    assert MODEL_VERSION in card
    assert "Хардтоп (купе)" in card

    overview = format_presets_overview(service)
    assert "Toyota" in overview
    assert "Вероятность:" in overview
    assert "₽" in overview
    assert "$" not in overview
    assert "USD" not in overview

    history_str = format_history(
        [
            {
                "timestamp": "2026-04-01T12:00:00",
                "brand": "toyota",
                "carbody": "sedan",
                "predicted_price_usd": 10000.0,
                "predicted_price_rub": 935000.0,
                "model_name": "Случайный лес v2.2",
            }
        ]
    )
    assert "₽" in history_str
    assert "$" not in history_str
    assert "Седан" in history_str
    assert "пуста" in format_history([])

    # Сравнение с рынком только в рублях
    cmp_str = compare_to_market(15000.0, [10000.0, 12000.0, 14000.0])
    assert "₽" in cmp_str
    assert "$" not in cmp_str

    # Клавиатуры: кнопка Справка, русские кузова, модели с версиями
    menu_texts = [btn.text for row in main_menu_kb().keyboard for btn in row]
    assert BTN_HELP in menu_texts

    assert len(presets_kb().inline_keyboard) == len(CAR_PRESETS)
    assert brands_kb().inline_keyboard

    body_texts = [row[0].text for row in bodies_kb().inline_keyboard]
    for ru_label in BODY_LABELS.values():
        assert ru_label in body_texts

    model_texts = [row[0].text for row in models_kb(metrics).inline_keyboard]
    assert len(model_texts) == len(MODEL_NAMES)
    for txt in model_texts:
        assert MODEL_VERSION in txt
        assert "R²=" in txt


def test_metadata_contains_model_versions():
    """Проверяет версионирование моделей и размеры выборок в models/metadata.json."""
    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        meta = json.load(f)
    assert meta["model_version"] == MODEL_VERSION
    assert meta["train_samples"] == 164
    assert meta["test_samples"] == 41
    assert set(meta["model_versions"].keys()) == {
        "random_forest",
        "linear_regression",
        "neural_network",
        "knn",
    }


def test_bot_dispatcher_builds():
    dp = create_dispatcher(ModelService())
    assert dp is not None
