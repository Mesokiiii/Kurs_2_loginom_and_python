"""Функции отрисовки аналитических графиков OLAP для Matplotlib."""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter


def render_brand_top10(ax, df, lbl):
    brand_stats = df.groupby("brand")["price"].mean().sort_values(ascending=True).tail(10)
    bars = ax.barh(brand_stats.index.str.capitalize(), brand_stats.values, color="#38bdf8", edgecolor="#0284c7")
    ax.set_title("Топ-10 марок по средней рыночной цене ($)", color="#f8fafc", fontsize=12, weight="bold")
    ax.set_xlabel("Средняя цена ($)", color="#cbd5e1", fontsize=10)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, p: f"${x:,.0f}"))
    ax.bar_label(bars, fmt="${:,.0f}", padding=4, color="#e2e8f0", fontsize=8)
    lbl.configure(text=f"💡 Топ бренды: Jaguar (${brand_stats.get('jaguar', 0):,.0f}), Buick (${brand_stats.get('buick', 0):,.0f}) и Porsche (${brand_stats.get('porsche', 0):,.0f}).")


def render_body_comparison(ax, df, lbl):
    body_stats = df.groupby("carbody")["price"].agg(["mean", "median", "count"]).sort_values("mean", ascending=False)
    x_pos = np.arange(len(body_stats))
    w = 0.35
    b1 = ax.bar(x_pos - w/2, body_stats["mean"], w, label="Средняя цена", color="#38bdf8")
    ax.bar(x_pos + w/2, body_stats["median"], w, label="Медиана", color="#10b981")
    ax.set_xticks(x_pos)
    ax.set_xticklabels(body_stats.index.str.capitalize(), color="#cbd5e1")
    ax.set_title("Сравнение цен по типам кузова автомобиля ($)", color="#f8fafc", fontsize=12, weight="bold")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f"${x:,.0f}"))
    ax.legend(facecolor="#1e293b", edgecolor="#334155", labelcolor="#cbd5e1", fontsize=9)
    ax.bar_label(b1, fmt="${:,.0f}", padding=3, color="#93c5fd", fontsize=8)
    lbl.configure(text=f"💡 Седаны и хэтчбеки составляют основу рынка. Кабриолеты и хардтопы — самые дорогие.")


def render_hp_scatter(ax, fig, df, lbl):
    sc = ax.scatter(df["horsepower"], df["price"], c=df["enginesize"], cmap="viridis", alpha=0.85, s=40)
    z = np.polyfit(df["horsepower"], df["price"], 1)
    p = np.poly1d(z)
    ax.plot(df["horsepower"], p(df["horsepower"]), "--", color="#f59e0b", label="Линия тренда", linewidth=1.5)
    ax.set_title("Зависимость стоимости от мощности двигателя (л.с.)", color="#f8fafc", fontsize=12, weight="bold")
    ax.set_xlabel("Мощность (л.с.)", color="#cbd5e1", fontsize=10)
    ax.set_ylabel("Цена ($)", color="#cbd5e1", fontsize=10)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f"${x:,.0f}"))
    ax.legend(facecolor="#1e293b", edgecolor="#334155", labelcolor="#cbd5e1", fontsize=9)
    corr = df["horsepower"].corr(df["price"])
    lbl.configure(text=f"💡 Корреляция мощности и цены: r = {corr:.3f} (сильная связь). Рост на 10 л.с. дает +${z[0]*10:,.0f}.")


def render_fuel_pie(ax, df, lbl):
    stats = df.groupby("fueltype")["price"].agg(["mean", "count"])
    ax.pie(stats["count"], labels=[f"{k.capitalize()} ({int(v)} шт.)" for k, v in stats["count"].items()],
           autopct="%1.1f%%", colors=["#38bdf8", "#10b981"], textprops={"color": "white", "fontsize": 10}, startangle=140)
    ax.set_title("Доля автомобилей по типам топлива", color="#f8fafc", fontsize=12, weight="bold")
    lbl.configure(text="💡 90% авто оснащены бензиновыми двигателями, 10% — дизельными с более высокой ценой.")
