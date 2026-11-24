"""Раздел OLAP-аналитики рынка автомобилей."""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import streamlit as st


def render_olap_page(df: pd.DataFrame) -> None:
    """Отрисовывает ключевые показатели рынка и интерактивные графики."""
    st.header("OLAP-аналитика рынка")

    if df.empty:
        st.warning("Данные рынка не найдены.")
        return

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Автомобилей в базе", f"{len(df)}")
    k2.metric("Средняя цена", f"${df['price'].mean():,.0f}")
    k3.metric("Медиана рынка", f"${df['price'].median():,.0f}")
    k4.metric("Максимум (Люкс)", f"${df['price'].max():,.0f}")

    options = [
        "Средняя цена по маркам (Топ-10)",
        "Цены по типам кузова",
        "Зависимость: Мощность vs Цена",
        "Распределение по типу топлива",
    ]
    choice = st.selectbox("Выберите срез", options)

    fig, ax = plt.subplots(figsize=(9, 4.5), dpi=110)

    if choice == options[0]:
        stats = df.groupby("brand")["price"].mean().sort_values(ascending=True).tail(10)
        bars = ax.barh(stats.index.str.capitalize(), stats.values, color="#2563eb")
        ax.set_title("Топ-10 марок по средней цене ($)")
        ax.set_xlabel("Средняя цена ($)")
        ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"${x:,.0f}"))
        ax.bar_label(bars, fmt="${:,.0f}", padding=4, fontsize=8)
    elif choice == options[1]:
        stats = df.groupby("carbody")["price"].agg(["mean", "median"]).sort_values("mean", ascending=False)
        x = np.arange(len(stats))
        w = 0.35
        b1 = ax.bar(x - w / 2, stats["mean"], w, label="Средняя", color="#2563eb")
        ax.bar(x + w / 2, stats["median"], w, label="Медиана", color="#10b981")
        ax.set_xticks(x)
        ax.set_xticklabels(stats.index.str.capitalize())
        ax.set_title("Сравнение цен по типам кузова ($)")
        ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f"${y:,.0f}"))
        ax.bar_label(b1, fmt="${:,.0f}", padding=3, fontsize=8)
        ax.legend()
    elif choice == options[2]:
        ax.scatter(df["horsepower"], df["price"], c=df["enginesize"], cmap="viridis", alpha=0.8, s=40)
        z = np.polyfit(df["horsepower"], df["price"], 1)
        ax.plot(df["horsepower"], np.poly1d(z)(df["horsepower"]), "--", color="#f59e0b", label="Тренд")
        ax.set_title("Зависимость цены от мощности (л.с.)")
        ax.set_xlabel("Мощность (л.с.)")
        ax.set_ylabel("Цена ($)")
        ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f"${y:,.0f}"))
        ax.legend()
        corr = df["horsepower"].corr(df["price"])
        st.caption(f"Корреляция мощности и цены: r = {corr:.3f}")
    else:
        stats = df.groupby("fueltype")["price"].count()
        labels = [f"{k.capitalize()} ({int(v)} шт.)" for k, v in stats.items()]
        ax.pie(stats.values, labels=labels, autopct="%1.1f%%", colors=["#2563eb", "#10b981"], startangle=140)
        ax.set_title("Доля автомобилей по типам топлива")

    ax.grid(axis="x" if choice == options[0] else "y", alpha=0.25)
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)
