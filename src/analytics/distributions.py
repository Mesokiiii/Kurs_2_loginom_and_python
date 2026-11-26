"""Визуализация распределений цен (в тыс. руб.) и разброса по маркам автомобилей."""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from src.analytics.styles import (
    PALETTE,
    BRAND_DISPLAY_NAMES,
    configure_matplotlib,
    usd_to_krub,
    format_thousands,
    krub_tick_formatter,
    style_axes,
    save_figure,
)


def plot_price_distribution(df: pd.DataFrame) -> None:
    """Распределение цен автомобилей в тыс. руб. и логарифмическом масштабе."""
    configure_matplotlib()
    fig, axes = plt.subplots(1, 2, figsize=(15.5, 6.2))

    prices_krub = usd_to_krub(df["price"])
    mean_krub = float(prices_krub.mean())
    median_krub = float(prices_krub.median())
    skew_raw = float(prices_krub.skew())
    max_krub = float(prices_krub.max())

    # Панель 1: Исходное распределение цен в тыс. руб.
    ax0 = axes[0]
    sns.histplot(
        prices_krub,
        kde=True,
        ax=ax0,
        color=PALETTE["teal"],
        edgecolor=PALETTE["white"],
        linewidth=0.8,
        alpha=0.82,
        bins=22,
        line_kws={"linewidth": 2.4, "color": PALETTE["graphite"]},
    )
    ax0.axvline(
        mean_krub,
        color=PALETTE["burgundy"],
        linestyle="--",
        linewidth=2.4,
        label=f"Среднее: {format_thousands(mean_krub)} тыс. руб.",
    )
    ax0.axvline(
        median_krub,
        color=PALETTE["terracotta"],
        linestyle="-",
        linewidth=2.4,
        label=f"Медиана: {format_thousands(median_krub)} тыс. руб.",
    )
    style_axes(ax0, grid_axis="y")
    ax0.set_title("Распределение цен автомобилей (тыс. руб.)", fontsize=15.5, fontweight="bold", pad=12)
    ax0.set_xlabel("Цена автомобиля (тыс. руб.)", fontsize=13.5, fontweight="bold")
    ax0.set_ylabel("Количество автомобилей (шт.)", fontsize=13.5, fontweight="bold")
    ax0.xaxis.set_major_formatter(krub_tick_formatter())
    ax0.legend(loc="upper right", frameon=True, facecolor=PALETTE["white"], fontsize=11.5)

    skew_str = f"{skew_raw:.2f}".replace(".", ",")
    skew_note = (
        f"Правосторонняя асимметрия: {skew_str}\n"
        f"Большинство авто стоит до 1 500 тыс. руб.,\n"
        f"премиум-сегмент достигает {format_thousands(max_krub)} тыс. руб."
    )
    ax0.text(
        0.97,
        0.72,
        skew_note,
        transform=ax0.transAxes,
        ha="right",
        va="top",
        fontsize=10.8,
        color=PALETTE["graphite"],
        bbox=dict(
            boxstyle="round,pad=0.5",
            fc=PALETTE["white"],
            ec=PALETTE["teal"],
            lw=1.3,
        ),
    )

    # Панель 2: Логарифмическое распределение цены
    ax1 = axes[1]
    log_prices = np.log(prices_krub)
    log_mean = float(log_prices.mean())
    log_median = float(log_prices.median())
    log_skew = float(log_prices.skew())

    sns.histplot(
        log_prices,
        kde=True,
        ax=ax1,
        color=PALETTE["soft_teal"],
        edgecolor=PALETTE["white"],
        linewidth=0.8,
        alpha=0.82,
        bins=22,
        line_kws={"linewidth": 2.4, "color": PALETTE["graphite"]},
    )
    ax1.axvline(
        log_mean,
        color=PALETTE["burgundy"],
        linestyle="--",
        linewidth=2.4,
        label=f"Среднее: {log_mean:.2f}".replace(".", ","),
    )
    ax1.axvline(
        log_median,
        color=PALETTE["terracotta"],
        linestyle="-",
        linewidth=2.4,
        label=f"Медиана: {log_median:.2f}".replace(".", ","),
    )
    style_axes(ax1, grid_axis="y")
    ax1.set_ylim(0, ax1.get_ylim()[1] * 1.18)
    ax1.set_title("Логарифмированное распределение ln(Цена)", fontsize=15.5, fontweight="bold", pad=12)
    ax1.set_xlabel("Натуральный логарифм цены ln(тыс. руб.)", fontsize=13.5, fontweight="bold")
    ax1.set_ylabel("Количество автомобилей (шт.)", fontsize=13.5, fontweight="bold")
    ax1.legend(loc="upper right", frameon=True, facecolor=PALETTE["white"], fontsize=11.5)

    log_skew_str = f"{log_skew:.2f}".replace(".", ",")
    log_note = (
        f"Асимметрия после ln: {log_skew_str}\n"
        f"Симметричная форма подтверждает\n"
        f"устойчивость регрессионных оценок"
    )
    ax1.text(
        0.97,
        0.74,
        log_note,
        transform=ax1.transAxes,
        ha="right",
        va="top",
        fontsize=10.8,
        color=PALETTE["graphite"],
        bbox=dict(
            boxstyle="round,pad=0.5",
            fc=PALETTE["white"],
            ec=PALETTE["soft_teal"],
            lw=1.3,
        ),
    )

    fig.suptitle(
        "Статистический анализ распределения рыночной стоимости (n = 205 автомобилей, цены в рублях)",
        fontsize=16.2,
        fontweight="bold",
        color=PALETTE["graphite"],
        y=1.02,
    )
    plt.tight_layout()
    save_figure(fig, "price_distribution.png")


def plot_brand_vs_price(df: pd.DataFrame) -> None:
    """Горизонтальная диаграмма размаха цен (в тыс. руб.) по маркам автомобилей."""
    if "brand" not in df.columns:
        return

    configure_matplotlib()
    plot_df = df[["brand", "price"]].copy()
    plot_df["price_krub"] = usd_to_krub(plot_df["price"])
    plot_df["brand_label"] = plot_df["brand"].map(
        lambda b: BRAND_DISPLAY_NAMES.get(str(b).lower(), str(b).capitalize())
    )

    brand_stats = (
        plot_df.groupby("brand_label")["price_krub"]
        .agg(["median", "count", "max"])
        .sort_values("median", ascending=False)
    )
    order = brand_stats.index.tolist()
    n_brands = len(order)

    # Плавный переход оттенков: бордовый/изумрудный для премиума -> бирюзовый -> графитово-серый
    colors = []
    for i in range(n_brands):
        ratio = i / max(n_brands - 1, 1)
        if ratio < 0.22:
            colors.append(PALETTE["burgundy"])
        elif ratio < 0.65:
            colors.append(PALETTE["teal"])
        else:
            colors.append(PALETTE["soft_teal"])

    palette_map = dict(zip(order, colors))

    fig, ax = plt.subplots(figsize=(13.5, 9.6))
    sns.boxplot(
        data=plot_df,
        y="brand_label",
        x="price_krub",
        hue="brand_label",
        legend=False,
        order=order,
        palette=palette_map,
        ax=ax,
        width=0.68,
        linewidth=1.3,
        fliersize=4.5,
        flierprops=dict(marker="o", markerfacecolor=PALETTE["graphite"], alpha=0.65, markeredgecolor="none"),
        medianprops=dict(color=PALETTE["white"], linewidth=2.2),
        whiskerprops=dict(color=PALETTE["graphite"], linewidth=1.2),
        capprops=dict(color=PALETTE["graphite"], linewidth=1.2),
    )

    market_median = float(plot_df["price_krub"].median())
    ax.axvline(
        market_median,
        color=PALETTE["terracotta"],
        linestyle="--",
        linewidth=2.0,
        zorder=4,
        label=f"Медиана рынка: {format_thousands(market_median)} тыс. руб.",
    )

    # Подписи медианной цены и числа авто справа от каждого размаха
    x_max = float(plot_df["price_krub"].max())
    ax.set_xlim(0, x_max * 1.19)
    for idx, brand in enumerate(order):
        med = brand_stats.loc[brand, "median"]
        cnt = int(brand_stats.loc[brand, "count"])
        bmax = float(brand_stats.loc[brand, "max"])
        if cnt == 1:
            ax.scatter(
                [med],
                [idx],
                s=95,
                marker="D",
                color=palette_map[brand],
                edgecolors=PALETTE["graphite"],
                linewidth=1.2,
                zorder=5,
            )
        ax.text(
            bmax + x_max * 0.018,
            idx,
            f"мед. {format_thousands(med)} (n={cnt})",
            va="center",
            ha="left",
            fontsize=10.2,
            fontweight="bold",
            color=PALETTE["graphite"],
        )

    style_axes(ax, grid_axis="x")
    ax.set_title(
        "Диапазон и медианная стоимость автомобилей по маркам (тыс. руб.)",
        fontsize=16,
        fontweight="bold",
        pad=14,
    )
    ax.set_xlabel("Цена автомобиля (тыс. руб.)", fontsize=13.5, fontweight="bold")
    ax.set_ylabel("Марка автомобиля", fontsize=13.5, fontweight="bold")
    ax.tick_params(axis="y", labelsize=11.5)
    ax.xaxis.set_major_formatter(krub_tick_formatter())
    ax.legend(loc="lower right", frameon=True, facecolor=PALETTE["white"], fontsize=12)

    plt.tight_layout()
    save_figure(fig, "brand_vs_price.png")
