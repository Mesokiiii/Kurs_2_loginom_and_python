"""Тесты для вероятности цены, веб-интерфейса Streamlit и Telegram-бота aiogram 3."""

from src.config import CAR_PRESETS, MODEL_NAMES
from src.models.service import ModelService
from src.bot.app import create_dispatcher
from src.bot.formatting import format_history, format_prediction, format_presets_overview
from src.bot.keyboards import bodies_kb, brands_kb, main_menu_kb, models_kb, presets_kb


def test_price_probability_for_all_models():
    service = ModelService()
    preset = CAR_PRESETS["Бюджетный хэтчбек (Toyota)"]

    results = service.predict_all_models(preset)
    assert len(results) == len(MODEL_NAMES)
    for res in results:
        assert res.price_usd > 0
        assert 5.0 <= res.price_probability <= 99.0


def test_presets_have_valid_price_and_probability():
    service = ModelService()
    for name, data in CAR_PRESETS.items():
        res = service.predict(data)
        assert res.price_usd > 0, f"Нулевая цена для пресета {name}"
        assert 5.0 <= res.price_probability <= 99.0


def test_bot_formatting_and_keyboards():
    service = ModelService()
    preset = CAR_PRESETS["Спорткар / Купе (Porsche)"]
    res = service.predict(preset)

    card = format_prediction(res, preset, title="Porsche")
    assert "Цена:" in card
    assert "Вероятность цены" in card
    assert f"{res.price_probability:.1f}%" in card

    overview = format_presets_overview(service)
    assert "Toyota" in overview
    assert "Вероятность:" in overview

    assert "пуста" in format_history([])
    assert main_menu_kb().keyboard
    assert len(presets_kb().inline_keyboard) == len(CAR_PRESETS)
    assert brands_kb().inline_keyboard
    assert bodies_kb().inline_keyboard
    assert len(models_kb().inline_keyboard) == len(MODEL_NAMES)


def test_bot_dispatcher_builds():
    dp = create_dispatcher(ModelService())
    assert dp is not None
