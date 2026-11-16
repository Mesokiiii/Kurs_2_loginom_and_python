"""Многомерные аналитические срезы OLAP."""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import seaborn as sns

from src.analytics.styles import save_figure


def plot_olap_body_fuel_price(df: pd.DataFrame) -> None:
    """Многомерный срез: тип кузова x тип топлива x средняя цена."""
    if not {"carbody", "fueltype", "price"}.issubset(df.columns):
        return

    pivot = df.pivot_table(index="carbody", columns="fueltype", values="price", aggfunc="mean")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5))

    sns.heatmap(pivot, annot=True, fmt=",.0f", cmap="YlGnBu", cbar_kws={"label": "Средняя цена ($)"}, ax=ax1, linewidths=1.0)
    ax1.set_title("OLAP-срез: Средняя цена по кузову и типу топлива", fontsize=12, fontweight="bold", pad=10)
    ax1.set_xlabel("Тип топлива", fontsize=11)
    ax1.set_ylabel("Тип кузова", fontsize=11)

    melted = df.groupby(["carbody", "fueltype"])["price"].mean().reset_index()
    sns.barplot(data=melted, x="carbody", y="price", hue="fueltype", palette="Set2", ax=ax2)
    ax2.set_title("Сравнение средней цены кузова по типам топлива", fontsize=12, fontweight="bold", pad=10)
    ax2.set_xlabel("Тип кузова", fontsize=11)
    ax2.set_ylabel("Средняя цена ($)", fontsize=11)
    ax2.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f"${x:,.0f}"))
    ax2.legend(title="Топливо", frameon=True)

    plt.tight_layout()
    save_figure(fig, "olap_body_fuel_price.png")


def plot_olap_engine_horsepower(df: pd.DataFrame) -> None:
    """Многомерная диаграмма: объем двигателя vs мощность vs цена."""
    fig, ax = plt.subplots(figsize=(10, 6))

    scatter = ax.scatter(
        df["enginesize"],
        df["horsepower"],
        c=df["price"],
        s=df["curbweight"] / 35.0,
        cmap="plasma",
        alpha=0.8,
        edgecolors="w",
        linewidth=0.5,
    )

    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label("Цена автомобиля ($)", fontsize=11)
    cbar.ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f"${x:,.0f}"))

    sns.regplot(
        data=df,
        x="enginesize",
        y="horsepower",
        scatter=False,
        ax=ax,
        color="#333333",
        label="Линия тренда",
        line_kws={"linestyle": "--", "linewidth": 1.5},
    )

    ax.set_title("OLAP-анализ: Объем двигателя, мощность, вес и цена", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Объем двигателя (enginesize, куб. дюймы)", fontsize=11)
    ax.set_ylabel("Мощность (horsepower, л.с.)", fontsize=11)
    ax.legend(frameon=True)

    plt.tight_layout()
    save_figure(fig, "olap_engine_horsepower.png")
