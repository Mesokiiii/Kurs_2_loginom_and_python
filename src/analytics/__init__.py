"""Пакет разведочного анализа данных и OLAP-визуализаций."""

import pandas as pd
from src.analytics.styles import (
    PALETTE,
    save_figure,
    configure_matplotlib,
    usd_to_krub,
    format_thousands,
)
from src.analytics.distributions import plot_price_distribution, plot_brand_vs_price
from src.analytics.correlations import plot_correlation_heatmap
from src.analytics.olap import plot_olap_body_fuel_price, plot_olap_engine_horsepower
from src.analytics.comparison import plot_model_comparison


def generate_all_eda_visualizations(df: pd.DataFrame) -> None:
    """Генерация полного комплекта графиков EDA, OLAP и сравнения с Loginom."""
    plot_price_distribution(df)
    plot_correlation_heatmap(df)
    plot_brand_vs_price(df)
    plot_olap_body_fuel_price(df)
    plot_olap_engine_horsepower(df)
    plot_model_comparison({})


__all__ = [
    "PALETTE",
    "configure_matplotlib",
    "usd_to_krub",
    "format_thousands",
    "save_figure",
    "plot_price_distribution",
    "plot_brand_vs_price",
    "plot_correlation_heatmap",
    "plot_olap_body_fuel_price",
    "plot_olap_engine_horsepower",
    "plot_model_comparison",
    "generate_all_eda_visualizations",
]
