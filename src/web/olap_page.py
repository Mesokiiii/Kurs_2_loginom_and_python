"""Раздел OLAP-аналитики рынка автомобилей (все цены в рублях)."""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import streamlit as st

from src.config import (
    BODY_LABELS,
    DRIVE_LABELS,
    FUEL_LABELS,
    USD_TO_RUB_RATE,
    format_rub,
)

COLOR_PRIMARY = "#0F766E"
COLOR_SECONDARY = "#1E293B"
COLOR_ACCENT = "#9F1239"
COLOR_NEUTRAL = "#475569"


def _fmt_k_rub(val: float, _pos: int | None = None) -> str:
    return f"{val:,.0f} тыс. ₽".replace(",", " ")


def render_olap_page(df: pd.DataFrame) -> None:
    """Отрисовывает ключевые показатели рынка и интерактивные OLAP-графики в рублях."""
    st.header("OLAP-аналитика рынка автомобилей")

    if df.empty:
        st.warning("Данные рынка не найдены.")
        return

    df_rub = df.copy()
    df_rub["price_rub"] = df_rub["price"] * USD_TO_RUB_RATE
    df_rub["price_k_rub"] = df_rub["price_rub"] / 1000.0

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Автомобилей в выборке", f"{len(df_rub)}")
    k2.metric("Средняя цена (₽)", format_rub(df_rub["price_rub"].mean()))
    k3.metric("Медиана рынка (₽)", format_rub(df_rub["price_rub"].median()))
    k4.metric("Максимум / Люкс (₽)", format_rub(df_rub["price_rub"].max()))

    options = [
        "Средняя цена по маркам (Топ-10)",
        "Цены по типам кузова",
        "Зависимость: Мощность vs Цена",
        "Распределение по типу топлива",
        "Цены по типу привода (FWD / RWD / 4WD)",
    ]
    choice = st.selectbox("Выберите аналитический срез", options)

    fig, ax = plt.subplots(figsize=(9.2, 4.6), dpi=110)

    if choice == options[0]:
        stats = df_rub.groupby("brand")["price_k_rub"].mean().sort_values(ascending=True).tail(10)
        bars = ax.barh(stats.index.str.capitalize(), stats.values, color=COLOR_PRIMARY)
        ax.set_title("Топ-10 марок по средней цене (тыс. руб.)")
        ax.set_xlabel("Средняя цена (тыс. руб.)")
        ax.xaxis.set_major_formatter(FuncFormatter(_fmt_k_rub))
        ax.bar_label(bars, labels=[f"{v:,.0f} тыс. ₽".replace(",", " ") for v in stats.values], padding=4, fontsize=8)
    elif choice == options[1]:
        stats = df_rub.groupby("carbody")["price_k_rub"].agg(["mean", "median"]).sort_values("mean", ascending=False)
        labels = [BODY_LABELS.get(idx, str(idx).capitalize()) for idx in stats.index]
        x = np.arange(len(stats))
        w = 0.36
        b1 = ax.bar(x - w / 2, stats["mean"], w, label="Средняя цена", color=COLOR_PRIMARY)
        ax.bar(x + w / 2, stats["median"], w, label="Медианная цена", color=COLOR_SECONDARY)
        ax.set_xticks(x)
        ax.set_xticklabels(labels)
        ax.set_title("Сравнение цен по типам кузова (тыс. руб.)")
        ax.set_ylabel("Цена (тыс. руб.)")
        ax.yaxis.set_major_formatter(FuncFormatter(_fmt_k_rub))
        ax.bar_label(b1, labels=[f"{v:,.0f}".replace(",", " ") for v in stats["mean"]], padding=3, fontsize=8)
        ax.legend()
    elif choice == options[2]:
        sc = ax.scatter(
            df_rub["horsepower"],
            df_rub["price_k_rub"],
            c=df_rub["enginesize"],
            cmap="GnBu",
            alpha=0.85,
            s=42,
            edgecolors=COLOR_SECONDARY,
            linewidths=0.4,
        )
        z = np.polyfit(df_rub["horsepower"], df_rub["price_k_rub"], 1)
        x_line = np.linspace(df_rub["horsepower"].min(), df_rub["horsepower"].max(), 100)
        ax.plot(x_line, np.poly1d(z)(x_line), "--", color=COLOR_ACCENT, linewidth=2.0, label="Линейный тренд")
        cbar = fig.colorbar(sc, ax=ax)
        cbar.set_label("Объём двигателя (куб. дюймы)")
        ax.set_title("Зависимость стоимости (тыс. руб.) от мощности двигателя (л.с.)")
        ax.set_xlabel("Мощность двигателя (л.с.)")
        ax.set_ylabel("Цена (тыс. руб.)")
        ax.yaxis.set_major_formatter(FuncFormatter(_fmt_k_rub))
        ax.legend()
        corr = df_rub["horsepower"].corr(df_rub["price_rub"])
        st.caption(f"Коэффициент корреляции Пирсона между мощностью и ценой: r = {corr:.3f}")
    elif choice == options[3]:
        stats = df_rub.groupby("fueltype")["price_rub"].count()
        labels = [f"{FUEL_LABELS.get(k, k)} ({int(v)} шт.)" for k, v in stats.items()]
        ax.pie(
            stats.values,
            labels=labels,
            autopct="%1.1f%%",
            colors=[COLOR_PRIMARY, COLOR_ACCENT],
            startangle=140,
            textprops={"fontsize": 10},
        )
        ax.set_title("Доля автомобилей в выборке по типу топлива")
    else:
        stats = df_rub.groupby("drivewheel")["price_k_rub"].agg(["mean", "median", "count"]).sort_values("mean", ascending=False)
        labels = [f"{DRIVE_LABELS.get(idx, idx)}\n({int(row['count'])} авто)" for idx, row in stats.iterrows()]
        x = np.arange(len(stats))
        w = 0.36
        b1 = ax.bar(x - w / 2, stats["mean"], w, label="Средняя цена", color=COLOR_PRIMARY)
        ax.bar(x + w / 2, stats["median"], w, label="Медианная цена", color=COLOR_NEUTRAL)
        ax.set_xticks(x)
        ax.set_xticklabels(labels)
        ax.set_title("Цены автомобилей по типу привода (тыс. руб.)")
        ax.set_ylabel("Цена (тыс. руб.)")
        ax.yaxis.set_major_formatter(FuncFormatter(_fmt_k_rub))
        ax.bar_label(b1, labels=[f"{v:,.0f} тыс. ₽".replace(",", " ") for v in stats["mean"]], padding=3, fontsize=8)
        ax.legend()

    if choice != options[3]:
        ax.grid(axis="x" if choice == options[0] else "y", alpha=0.25)
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)
