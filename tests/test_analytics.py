"""Модульные тесты для пакета аналитики и OLAP-визуализации."""

import pytest
import pandas as pd
from pathlib import Path

from src.data.data_loader import load_raw_data
from src.data.preprocessor import clean_car_dataframe
from src.analytics.visualizations import (
    plot_price_distribution,
    plot_correlation_heatmap,
    plot_brand_vs_price,
    plot_olap_body_fuel_price,
    plot_olap_engine_horsepower,
    plot_model_comparison,
)
from src.config import FIGURES_DIR


@pytest.fixture(scope="module")
def sample_clean_df() -> pd.DataFrame:
    """Фикстура с предобработанными данными для тестов визуализации."""
    raw_df = load_raw_data()
    return clean_car_dataframe(raw_df)


def test_plot_price_distribution(sample_clean_df: pd.DataFrame) -> None:
    """Проверка генерации графика распределения цен."""
    plot_price_distribution(sample_clean_df)
    target_file = FIGURES_DIR / "price_distribution.png"
    assert target_file.exists()
    assert target_file.stat().st_size > 0


def test_plot_correlation_heatmap(sample_clean_df: pd.DataFrame) -> None:
    """Проверка генерации тепловой карты корреляций."""
    plot_correlation_heatmap(sample_clean_df)
    target_file = FIGURES_DIR / "correlation_heatmap.png"
    assert target_file.exists()
    assert target_file.stat().st_size > 0


def test_plot_brand_vs_price(sample_clean_df: pd.DataFrame) -> None:
    """Проверка генерации графика цен по маркам автомобилей."""
    plot_brand_vs_price(sample_clean_df)
    target_file = FIGURES_DIR / "brand_vs_price.png"
    assert target_file.exists()
    assert target_file.stat().st_size > 0


def test_plot_olap_slices(sample_clean_df: pd.DataFrame) -> None:
    """Проверка генерации OLAP-срезов."""
    plot_olap_body_fuel_price(sample_clean_df)
    plot_olap_engine_horsepower(sample_clean_df)

    assert (FIGURES_DIR / "olap_body_fuel_price.png").exists()
    assert (FIGURES_DIR / "olap_engine_horsepower.png").exists()


def test_plot_model_comparison() -> None:
    """Проверка построения графика сравнения метрик с Loginom."""
    plot_model_comparison({})
    target_file = FIGURES_DIR / "model_comparison_metrics.png"
    assert target_file.exists()
    assert target_file.stat().st_size > 0
