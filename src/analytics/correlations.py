"""Построение корреляционных тепловых карт с русскими названиями признаков."""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from src.analytics.styles import (
    PALETTE,
    TEAL_BURGUNDY_CMAP,
    FEATURE_RU_NAMES,
    configure_matplotlib,
    save_figure,
)


def plot_correlation_heatmap(df: pd.DataFrame) -> None:
    """Тепловая карта корреляции Пирсона числовых признаков с ценой автомобиля."""
    configure_matplotlib()
    num_cols = [
        "enginesize",
        "curbweight",
        "horsepower",
        "carwidth",
        "carlength",
        "wheelbase",
        "boreratio",
        "citympg",
        "highwaympg",
        "price",
    ]
    available_cols = [c for c in num_cols if c in df.columns]
    corr = df[available_cols].corr()

    ru_labels = [FEATURE_RU_NAMES.get(col, col) for col in available_cols]
    corr.index = ru_labels
    corr.columns = ru_labels

    fig, ax = plt.subplots(figsize=(12.8, 10.2))
    mask = np.triu(np.ones_like(corr, dtype=bool), k=1)

    hm = sns.heatmap(
        corr,
        mask=mask,
        cmap=TEAL_BURGUNDY_CMAP,
        vmax=1.0,
        vmin=-1.0,
        center=0.0,
        annot=True,
        fmt=".2f",
        annot_kws={"size": 11.5, "weight": "bold"},
        square=True,
        linewidths=1.0,
        linecolor=PALETTE["white"],
        cbar_kws={"shrink": 0.82, "pad": 0.03},
        ax=ax,
    )

    cbar = hm.collections[0].colorbar
    cbar.set_label("Коэффициент корреляции Пирсона (r)", fontsize=13, fontweight="bold", labelpad=12)
    cbar.ax.tick_params(labelsize=11.5)

    ax.set_title(
        "Корреляционная матрица технических характеристик и цены автомобиля",
        fontsize=16,
        fontweight="bold",
        pad=16,
    )
    ax.set_xticklabels(ax.get_xticklabels(), rotation=35, ha="right", fontsize=12, fontweight="bold")
    ax.set_yticklabels(ax.get_yticklabels(), rotation=0, fontsize=12, fontweight="bold")

    plt.tight_layout()
    save_figure(fig, "correlation_heatmap.png")
