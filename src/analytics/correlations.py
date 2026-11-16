"""Построение корреляционных тепловых карт."""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from src.analytics.styles import save_figure


def plot_correlation_heatmap(df: pd.DataFrame) -> None:
    """Тепловая карта корреляции числовых признаков с ценой."""
    num_cols = [
        "wheelbase", "carlength", "carwidth", "curbweight",
        "enginesize", "boreratio", "horsepower", "citympg", "highwaympg", "price",
    ]
    available_cols = [c for c in num_cols if c in df.columns]
    corr = df[available_cols].corr()

    fig, ax = plt.subplots(figsize=(11, 8))
    mask = np.triu(np.ones_like(corr, dtype=bool))
    cmap = sns.diverging_palette(230, 20, as_cmap=True)

    sns.heatmap(
        corr,
        mask=mask,
        cmap=cmap,
        vmax=1.0,
        vmin=-1.0,
        center=0,
        annot=True,
        fmt=".2f",
        square=True,
        linewidths=0.7,
        cbar_kws={"shrink": 0.8, "label": "Коэффициент корреляции Пирсона"},
        ax=ax,
    )
    ax.set_title("Корреляционная матрица числовых характеристик с ценой", fontsize=13, fontweight="bold", pad=15)
    plt.tight_layout()
    save_figure(fig, "correlation_heatmap.png")
