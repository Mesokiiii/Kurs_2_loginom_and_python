"""Многомерные аналитические срезы OLAP в рублях с русскоязычными подписями."""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from src.analytics.styles import (
    PALETTE,
    TEAL_SEQ_CMAP,
    PRICE_CMAP,
    BODY_RU_NAMES,
    FUEL_RU_NAMES,
    configure_matplotlib,
    usd_to_krub,
    format_thousands,
    krub_tick_formatter,
    style_axes,
    save_figure,
)


def plot_olap_body_fuel_price(df: pd.DataFrame) -> None:
    """OLAP-срез: тип кузова × тип топлива × средняя цена (тыс. руб.)."""
    if not {"carbody", "fueltype", "price"}.issubset(df.columns):
        return

    configure_matplotlib()
    work = df[["carbody", "fueltype", "price"]].copy()
    work["price_krub"] = usd_to_krub(work["price"])
    work["body_ru"] = work["carbody"].map(lambda x: BODY_RU_NAMES.get(str(x).lower(), str(x)))
    work["fuel_ru"] = work["fueltype"].map(lambda x: FUEL_RU_NAMES.get(str(x).lower(), str(x)))

    body_order = (
        work.groupby("body_ru")["price_krub"]
        .mean()
        .sort_values(ascending=False)
        .index.tolist()
    )
    fuel_order = ["Бензин", "Дизель"]

    pivot = work.pivot_table(
        index="body_ru",
        columns="fuel_ru",
        values="price_krub",
        aggfunc="mean",
    ).reindex(index=body_order, columns=fuel_order)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6.4), gridspec_kw={"width_ratios": [1.0, 1.28]})

    # Панель 1: Тепловая OLAP-матрица
    annot_labels = pivot.map(
        lambda v: f"{format_thousands(v)}\nтыс. руб." if pd.notna(v) else "Нет\nданных"
    )
    hm = sns.heatmap(
        pivot,
        annot=annot_labels,
        fmt="",
        annot_kws={"size": 12, "weight": "bold"},
        cmap=TEAL_SEQ_CMAP,
        linewidths=2.0,
        linecolor=PALETTE["white"],
        cbar_kws={"label": "Средняя цена (тыс. руб.)", "shrink": 0.88},
        ax=ax1,
    )
    # Выделяем отсутствующую ячейку (например, Кабриолет × Дизель) мягким серым фоном и подписью
    ax1.set_facecolor("#E2E8F0")
    for r_idx in range(pivot.shape[0]):
        for c_idx in range(pivot.shape[1]):
            if pd.isna(pivot.iloc[r_idx, c_idx]):
                ax1.text(
                    c_idx + 0.5,
                    r_idx + 0.5,
                    "Нет данных",
                    ha="center",
                    va="center",
                    fontsize=11.5,
                    fontweight="bold",
                    color=PALETTE["slate"],
                )
    cbar = hm.collections[0].colorbar
    cbar.set_label("Средняя цена (тыс. руб.)", fontsize=12.5, fontweight="bold", labelpad=10)
    cbar.ax.yaxis.set_major_formatter(krub_tick_formatter())
    cbar.ax.tick_params(labelsize=11)

    ax1.set_title("OLAP-матрица: Кузов × Топливо", fontsize=15, fontweight="bold", pad=12)
    ax1.set_xlabel("Тип топлива", fontsize=13, fontweight="bold")
    ax1.set_ylabel("Тип кузова", fontsize=13, fontweight="bold")
    ax1.set_xticklabels(ax1.get_xticklabels(), fontsize=12, fontweight="bold", rotation=0)
    ax1.set_yticklabels(ax1.get_yticklabels(), fontsize=12, fontweight="bold", rotation=0)

    # Панель 2: Сгруппированная столбчатая диаграмма
    x = np.arange(len(body_order))
    width = 0.37
    gas_vals = [pivot.loc[b, "Бензин"] if pd.notna(pivot.loc[b, "Бензин"]) else 0.0 for b in body_order]
    diesel_vals = [pivot.loc[b, "Дизель"] if pd.notna(pivot.loc[b, "Дизель"]) else 0.0 for b in body_order]

    bars_gas = ax2.bar(
        x - width / 2,
        gas_vals,
        width,
        label="Бензин",
        color=PALETTE["teal"],
        edgecolor=PALETTE["white"],
        linewidth=0.8,
    )
    bars_diesel = ax2.bar(
        x + width / 2,
        diesel_vals,
        width,
        label="Дизель",
        color=PALETTE["burgundy"],
        edgecolor=PALETTE["white"],
        linewidth=0.8,
    )

    max_val = max(max(gas_vals), max(diesel_vals))
    ax2.set_ylim(0, max_val * 1.18)

    for bar in bars_gas:
        h = bar.get_height()
        if h > 0:
            ax2.text(
                bar.get_x() + bar.get_width() / 2,
                h + max_val * 0.018,
                format_thousands(h),
                ha="center",
                va="bottom",
                fontsize=11,
                fontweight="bold",
                color=PALETTE["teal"],
            )
    for bar in bars_diesel:
        h = bar.get_height()
        if h > 0:
            ax2.text(
                bar.get_x() + bar.get_width() / 2,
                h + max_val * 0.018,
                format_thousands(h),
                ha="center",
                va="bottom",
                fontsize=11,
                fontweight="bold",
                color=PALETTE["burgundy"],
            )
        else:
            ax2.text(
                bar.get_x() + bar.get_width() / 2,
                max_val * 0.02,
                "—",
                ha="center",
                va="bottom",
                fontsize=11.5,
                color=PALETTE["slate"],
            )

    style_axes(ax2, grid_axis="y")
    ax2.set_title("Сравнение средней цены по кузову и топливу", fontsize=15, fontweight="bold", pad=12)
    ax2.set_xlabel("Тип кузова", fontsize=13, fontweight="bold")
    ax2.set_ylabel("Средняя цена (тыс. руб.)", fontsize=13, fontweight="bold")
    ax2.set_xticks(x)
    ax2.set_xticklabels(body_order, fontsize=12, fontweight="bold")
    ax2.yaxis.set_major_formatter(krub_tick_formatter())
    ax2.legend(title="Тип топлива", loc="upper right", frameon=True, facecolor=PALETTE["white"])

    fig.suptitle(
        "Многомерный OLAP-срез: влияние типа кузова и топлива на цену автомобиля (тыс. руб.)",
        fontsize=16.5,
        fontweight="bold",
        y=1.02,
    )
    plt.tight_layout()
    save_figure(fig, "olap_body_fuel_price.png")


def plot_olap_engine_horsepower(df: pd.DataFrame) -> None:
    """Многомерная диаграмма рассеяния: объём двигателя × мощность × масса × цена (тыс. руб.)."""
    configure_matplotlib()
    fig, ax = plt.subplots(figsize=(12.8, 7.2))

    prices_krub = usd_to_krub(df["price"])
    corr_val = float(df["enginesize"].corr(df["horsepower"]))

    # Размер маркера пропорционален снаряжённой массе
    weight_norm = (df["curbweight"] - df["curbweight"].min()) / (
        df["curbweight"].max() - df["curbweight"].min() + 1e-9
    )
    sizes = 45 + weight_norm * 240

    scatter = ax.scatter(
        df["enginesize"],
        df["horsepower"],
        c=prices_krub,
        s=sizes,
        cmap=PRICE_CMAP,
        alpha=0.88,
        edgecolors=PALETTE["white"],
        linewidth=0.8,
        zorder=3,
    )

    cbar = plt.colorbar(scatter, ax=ax, pad=0.02)
    cbar.set_label("Цена автомобиля (тыс. руб.)", fontsize=13, fontweight="bold", labelpad=12)
    cbar.ax.yaxis.set_major_formatter(krub_tick_formatter())
    cbar.ax.tick_params(labelsize=11.5)

    sns.regplot(
        data=df,
        x="enginesize",
        y="horsepower",
        scatter=False,
        ax=ax,
        color=PALETTE["graphite"],
        label=f"Линейный тренд (r = {corr_val:.2f})".replace(".", ","),
        line_kws={"linestyle": "--", "linewidth": 2.4},
        ci=95,
    )

    # Легенда размеров маркеров (снаряжённая масса в кг; 1 lb ≈ 0,4536 кг)
    legend_weights_kg = [900, 1300, 1750]
    w_min_kg = df["curbweight"].min() * 0.4536
    w_max_kg = df["curbweight"].max() * 0.4536
    for w_kg in legend_weights_kg:
        w_n = np.clip((w_kg - w_min_kg) / (w_max_kg - w_min_kg + 1e-9), 0, 1)
        ax.scatter(
            [],
            [],
            s=45 + w_n * 240,
            color=PALETTE["teal"],
            alpha=0.75,
            edgecolors=PALETTE["white"],
            label=f"Масса ≈ {format_thousands(w_kg)} кг",
        )

    style_axes(ax, grid_axis="both")
    ax.set_title(
        "OLAP-анализ: объём двигателя, мощность, масса и стоимость автомобиля",
        fontsize=16,
        fontweight="bold",
        pad=14,
    )
    ax.set_xlabel("Объём двигателя (куб. дюймы)", fontsize=13.5, fontweight="bold")
    ax.set_ylabel("Мощность двигателя (л.с.)", fontsize=13.5, fontweight="bold")
    ax.legend(
        loc="upper left",
        frameon=True,
        facecolor=PALETTE["white"],
        fontsize=11.5,
        labelspacing=0.9,
        borderpad=0.7,
    )

    plt.tight_layout()
    save_figure(fig, "olap_engine_horsepower.png")
