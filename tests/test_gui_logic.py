"""Unit tests for Desktop GUI helper logic, presets loading, and data formats.
"""

import pytest
from src.config import CAR_PRESETS, USD_TO_RUB_RATE, FEATURE_DEFAULTS
from src.gui.app import CarPriceApp
from src.models.model_service import ModelService


def test_preset_definitions_integrity():
    """Verifies that all preset vehicles contain all mandatory ML features."""
    required_keys = [
        "brand",
        "carbody",
        "fueltype",
        "aspiration",
        "drivewheel",
        "horsepower",
        "enginesize",
        "curbweight",
        "citympg",
        "highwaympg",
    ]

    for name, data in CAR_PRESETS.items():
        for k in required_keys:
            assert k in data, f"Preset '{name}' is missing key '{k}'"
            assert data[k] is not None


def test_currency_conversion():
    """Verifies USD to RUB conversion accuracy."""
    price_usd = 10000.0
    expected_rub = price_usd * USD_TO_RUB_RATE
    assert expected_rub == 935000.0


def test_gui_initialization_and_methods():
    """Verifies that CarPriceApp instantiates properly and can collect inputs."""
    # Запуск окна в фоновом режиме без отображения на экране
    app = CarPriceApp()
    app.withdraw()  # Do not display window

    try:
        # Проверка сбора значений из формы
        inputs = app._collect_inputs()
        assert "brand" in inputs
        assert "carbody" in inputs
        assert "horsepower" in inputs
        assert inputs["horsepower"] > 0

        # Проверка загрузки пресета в форму
        preset = CAR_PRESETS["Бюджетный хэтчбек (Toyota)"]
        app._load_preset_to_form(preset)
        assert app.brand_menu.get() == "Toyota"
        assert app.body_menu.get() == "Hatchback"
        assert float(app.slider_vars["horsepower"].get()) == 68.0

        # Проверка корректной отрисовки графиков OLAP
        app._update_olap_chart("Средняя цена по маркам (Топ-10)")
        app._update_olap_chart("Цены по типам кузова (Boxplot / Bar)")
        app._update_olap_chart("Зависимость: Мощность vs Цена")
        app._update_olap_chart("Распределение по типу топлива")
    finally:
        app.destroy()
