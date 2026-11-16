"""Визуализация распределений цен и брендов."""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import seaborn as sns

from src.analytics.styles import save_figure


def plot_price_distribution(df: pd.DataFrame) -> None:
    """Распределение целевой переменной (цена в USD и log-цена)."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    prices = df["price"]
    log_prices = np.log1p(prices)

    sns.histplot(prices, kde=True, ax=axes[0], color="#2b5c8f", bins=25)
    axes[0].axvline(prices.mean(), color="red", linestyle="--", linewidth=1.5, label=f"Среднее: ${prices.mean():,.0f}")
    axes[0].axvline(prices.median(), color="green", linestyle="-", linewidth=1.5, label=f"Медиана: ${prices.median():,.0f}")
    axes[0].set_title("Распределение цен автомобилей (USD)", fontsize=13, fontweight="bold", pad=10)
    axes[0].set_xlabel("Цена ($)", fontsize=11)
    axes[0].set_ylabel("Количество", fontsize=11)
    axes[0].legend(frameon=True)
    axes[0].text(0.70, 0.75, f"Асимметрия: {prices.skew():.2f}", transform=axes[0].transAxes,
                 bbox=dict(boxstyle="round,pad=0.4", fc="white", ec="#cccccc", lw=1))

    sns.histplot(log_prices, kde=True, ax=axes[1], color="#2e8b57", bins=25)
    axes[1].axvline(log_prices.mean(), color="red", linestyle="--", linewidth=1.5, label=f"Среднее: {log_prices.mean():.2f}")
    axes[1].axvline(log_prices.median(), color="green", linestyle="-", linewidth=1.5, label=f"Медиана: {log_prices.median():.2f}")
    axes[1].set_title("Логарифмическое распределение цены Log(Price)", fontsize=13, fontweight="bold", pad=10)
    axes[1].set_xlabel("Log(Цена)", fontsize=11)
    axes[1].set_ylabel("Количество", fontsize=11)
    axes[1].legend(frameon=True)

    plt.tight_layout()
    save_figure(fig, "price_distribution.png")


def plot_brand_vs_price(df: pd.DataFrame) -> None:
    """Диаграмма размаха (Boxplot) цен по маркам авто."""
    if "brand" not in df.columns:
        return

    order = df.groupby("brand")["price"].median().sort_values(ascending=False).index

    fig, ax = plt.subplots(figsize=(14, 6))
    sns.boxplot(
        data=df,
        x="brand",
        y="price",
        hue="brand",
        legend=False,
        order=order,
        palette="viridis",
        ax=ax,
        fliersize=3,
        linewidth=1.0,
    )
    ax.set_title("Распределение цен по маркам автомобилей", fontsize=13, fontweight="bold", pad=15)
    ax.set_xlabel("Марка автомобиля", fontsize=11)
    ax.set_ylabel("Цена ($)", fontsize=11)
    ax.tick_params(axis="x", rotation=45)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f"${x:,.0f}"))
    plt.tight_layout()
    save_figure(fig, "brand_vs_price.png")
