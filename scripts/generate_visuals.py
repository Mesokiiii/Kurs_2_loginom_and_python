"""Скрипт генерации полного комплекта аналитических графиков, ML-диаграмм,
архитектурных схем и QR-кода Telegram-бота в разрешении 300 DPI.

Все изображения сохраняются одновременно в `reports/figures/` и `screenshots/`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List

import joblib
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Polygon
import numpy as np
import pandas as pd
import qrcode
import seaborn as sns
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error
from sklearn.model_selection import train_test_split

# Добавляем корень проекта в sys.path при запуске скрипта напрямую
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (
    FIGURES_DIR,
    METRICS_PATH,
    MODELS_DIR,
    PREPROCESSOR_FILE,
    RANDOM_STATE,
    SCREENSHOTS_DIR,
    TARGET_COL,
    TEST_SIZE,
    USD_TO_RUB_RATE,
)
from src.data.data_loader import load_raw_data
from src.data.preprocessor import clean_car_dataframe
from src.analytics import generate_all_eda_visualizations
from src.analytics.styles import (
    BRAND_DISPLAY_NAMES,
    DRIVE_RU_NAMES,
    FEATURE_RU_NAMES,
    PALETTE,
    configure_matplotlib,
    format_thousands,
    krub_tick_formatter,
    save_figure,
    style_axes,
    usd_to_krub,
)


def _translate_feature_name(raw_name: str) -> str:
    """Переводит техническое имя признака sklearn в понятное русское название."""
    clean = raw_name
    for prefix in ("num__", "cat__"):
        if clean.startswith(prefix):
            clean = clean[len(prefix):]

    if clean in FEATURE_RU_NAMES:
        return FEATURE_RU_NAMES[clean]
    if clean.startswith("brand_"):
        brand = clean[len("brand_"):]
        return f"Марка: {BRAND_DISPLAY_NAMES.get(brand, brand.capitalize())}"
    if clean.startswith("carbody_"):
        body = clean[len("carbody_"):]
        body_map = {
            "hardtop": "Хардтоп",
            "convertible": "Кабриолет",
            "sedan": "Седан",
            "wagon": "Универсал",
            "hatchback": "Хэтчбек",
        }
        return f"Кузов: {body_map.get(body, body)}"
    if clean.startswith("drivewheel_"):
        drv = clean[len("drivewheel_"):]
        return f"Привод: {DRIVE_RU_NAMES.get(drv, drv)}"
    if clean.startswith("fueltype_"):
        fuel = clean[len("fueltype_"):]
        return "Топливо: Дизель" if fuel == "diesel" else "Топливо: Бензин"
    return clean


def plot_olap_drive_price(df: pd.DataFrame) -> None:
    """Средняя и медианная стоимость автомобиля (тыс. руб.) по типу привода."""
    configure_matplotlib()
    work = df[["drivewheel", "price"]].copy()
    work["price_krub"] = usd_to_krub(work["price"])
    work["drive_ru"] = work["drivewheel"].map(lambda d: DRIVE_RU_NAMES.get(str(d).lower(), str(d)))

    stats = (
        work.groupby("drive_ru")["price_krub"]
        .agg(["mean", "median", "count"])
        .sort_values("mean", ascending=False)
    )
    labels = [f"{name}\n(n = {int(row['count'])} авто)" for name, row in stats.iterrows()]
    means = stats["mean"].values
    medians = stats["median"].values
    market_mean = float(work["price_krub"].mean())

    fig, ax = plt.subplots(figsize=(12.4, 6.6))
    x = np.arange(len(labels))
    width = 0.35

    b_mean = ax.bar(
        x - width / 2,
        means,
        width,
        label="Средняя цена",
        color=PALETTE["teal"],
        edgecolor=PALETTE["white"],
        linewidth=0.9,
    )
    b_med = ax.bar(
        x + width / 2,
        medians,
        width,
        label="Медианная цена",
        color=PALETTE["soft_teal"],
        edgecolor=PALETTE["white"],
        linewidth=0.9,
    )

    ax.axhline(
        market_mean,
        color=PALETTE["burgundy"],
        linestyle="--",
        linewidth=2.2,
        label=f"Средняя по рынку: {format_thousands(market_mean)} тыс. руб.",
    )

    max_y = max(means.max(), medians.max())
    ax.set_ylim(0, max_y * 1.22)

    for bars, color in [(b_mean, PALETTE["teal"]), (b_med, PALETTE["graphite"])]:
        for bar in bars:
            h = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                h + max_y * 0.02,
                f"{format_thousands(h)} тыс. руб.",
                ha="center",
                va="bottom",
                fontsize=11.5,
                fontweight="bold",
                color=color,
            )

    style_axes(ax, grid_axis="y")
    ax.set_title(
        "OLAP-срез: стоимость автомобиля по типу привода (тыс. руб.)",
        fontsize=16,
        fontweight="bold",
        pad=14,
    )
    ax.set_xlabel("Тип привода", fontsize=13.5, fontweight="bold")
    ax.set_ylabel("Цена автомобиля (тыс. руб.)", fontsize=13.5, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=12, fontweight="bold")
    ax.yaxis.set_major_formatter(krub_tick_formatter())
    ax.legend(loc="upper right", frameon=True, facecolor=PALETTE["white"], fontsize=11.8)

    plt.tight_layout()
    save_figure(fig, "olap_drive_price.png")


def plot_feature_importance() -> None:
    """Топ-8 важнейших признаков обученной модели Random Forest."""
    configure_matplotlib()
    model = joblib.load(MODELS_DIR / "model_random_forest.joblib")
    preprocessor = joblib.load(MODELS_DIR / PREPROCESSOR_FILE)

    raw_names = list(preprocessor.transformer.get_feature_names_out())
    importances = np.asarray(model.feature_importances_, dtype=float) * 100.0

    top_k = 8
    idx = np.argsort(importances)[::-1][:top_k]
    top_names = [_translate_feature_name(raw_names[i]) for i in idx]
    top_vals = importances[idx]

    # Переворачиваем для отрисовки самого важного признака сверху
    top_names = top_names[::-1]
    top_vals = top_vals[::-1]

    # Градиент оттенков изумрудно-бирюзовой палитры
    bar_colors = [
        "#64748B",
        "#64748B",
        "#475569",
        "#2DD4BF",
        "#14B8A6",
        "#0D9488",
        "#0F766E",
        "#115E59",
    ]

    fig, ax = plt.subplots(figsize=(12.8, 6.8))
    y = np.arange(len(top_names))
    bars = ax.barh(
        y,
        top_vals,
        height=0.66,
        color=bar_colors,
        edgecolor=PALETTE["white"],
        linewidth=0.9,
    )

    max_v = float(top_vals.max())
    ax.set_xlim(0, max_v * 1.19)

    for bar, val in zip(bars, top_vals):
        ax.text(
            val + max_v * 0.015,
            bar.get_y() + bar.get_height() / 2,
            f"{val:.1f}%".replace(".", ","),
            va="center",
            ha="left",
            fontsize=12,
            fontweight="bold",
            color=PALETTE["graphite"],
        )

    top2_sum = float(top_vals[-1] + top_vals[-2])
    top8_sum = float(top_vals.sum())
    note = (
        f"Ключевой вывод:\n"
        f"2 главных признака формируют\n"
        f"{top2_sum:.1f}% значимости модели;\n"
        f"топ-8 признаков — {top8_sum:.1f}%"
    ).replace(".", ",")
    ax.text(
        0.97,
        0.16,
        note,
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=11.5,
        fontweight="bold",
        color=PALETTE["graphite"],
        bbox=dict(
            boxstyle="round,pad=0.6",
            fc=PALETTE["white"],
            ec=PALETTE["teal"],
            lw=1.6,
        ),
    )

    style_axes(ax, grid_axis="x")
    ax.set_title(
        "Важность признаков в модели «Случайный лес» (Random Forest, топ-8)",
        fontsize=16,
        fontweight="bold",
        pad=14,
    )
    ax.set_xlabel("Вклад признака в прогноз стоимости (%)", fontsize=13.5, fontweight="bold")
    ax.set_ylabel("Характеристика автомобиля", fontsize=13.5, fontweight="bold")
    ax.set_yticks(y)
    ax.set_yticklabels(top_names, fontsize=12, fontweight="bold")

    plt.tight_layout()
    save_figure(fig, "feature_importance.png")


def plot_residual_analysis(df: pd.DataFrame) -> None:
    """Двухпанельный анализ точности и остатков Random Forest на тестовой выборке (n = 41)."""
    configure_matplotlib()
    model = joblib.load(MODELS_DIR / "model_random_forest.joblib")
    preprocessor = joblib.load(MODELS_DIR / PREPROCESSOR_FILE)

    X = df.drop(columns=[TARGET_COL])
    y = df[TARGET_COL].values
    _, X_test, _, y_test_usd = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE
    )

    y_pred_usd = model.predict(preprocessor.transform(X_test))

    y_true = usd_to_krub(y_test_usd)
    y_pred = usd_to_krub(y_pred_usd)
    residuals = y_true - y_pred

    r2 = float(r2_score(y_true, y_pred))
    mae_krub = float(mean_absolute_error(y_true, y_pred))
    rmse_krub = float(root_mean_squared_error(y_true, y_pred))
    mape_pct = float(np.mean(np.abs(residuals / y_true)) * 100.0)
    within_15_pct = float(np.mean(np.abs(residuals / y_true) <= 0.15) * 100.0)

    fig, (ax0, ax1) = plt.subplots(1, 2, figsize=(16, 6.8))

    # --- Левая панель: Факт vs Прогноз + коридор ±15% ---
    lo = min(float(y_true.min()), float(y_pred.min())) * 0.85
    hi = max(float(y_true.max()), float(y_pred.max())) * 1.07
    grid = np.linspace(lo, hi, 200)

    ax0.fill_between(
        grid,
        grid * 0.85,
        grid * 1.15,
        color=PALETTE["soft_teal"],
        alpha=0.18,
        label="Коридор точности ±15%",
    )
    ax0.plot(grid, grid * 0.85, color=PALETTE["soft_teal"], linestyle=":", linewidth=1.3)
    ax0.plot(grid, grid * 1.15, color=PALETTE["soft_teal"], linestyle=":", linewidth=1.3)
    ax0.plot(
        grid,
        grid,
        color=PALETTE["burgundy"],
        linestyle="--",
        linewidth=2.2,
        label="Идеальный прогноз (y = x)",
    )
    ax0.scatter(
        y_true,
        y_pred,
        s=75,
        color=PALETTE["teal"],
        edgecolors=PALETTE["white"],
        linewidth=1.0,
        alpha=0.92,
        zorder=4,
        label=f"Тестовые авто (n = {len(y_true)})",
    )

    ax0.set_xlim(lo, hi)
    ax0.set_ylim(lo, hi)
    style_axes(ax0, grid_axis="both")
    ax0.set_title("Фактическая цена vs Прогноз (тыс. руб.)", fontsize=15.2, fontweight="bold", pad=12)
    ax0.set_xlabel("Фактическая цена (тыс. руб.)", fontsize=13.2, fontweight="bold")
    ax0.set_ylabel("Прогнозируемая цена (тыс. руб.)", fontsize=13.2, fontweight="bold")
    ax0.xaxis.set_major_formatter(krub_tick_formatter())
    ax0.yaxis.set_major_formatter(krub_tick_formatter())
    ax0.legend(loc="upper left", frameon=True, facecolor=PALETTE["white"], fontsize=11.2)

    badge_left = (
        f"R² (тест) = {r2:.4f}\n"
        f"В коридоре ±15%: {within_15_pct:.1f}% авто"
    ).replace(".", ",")
    ax0.text(
        0.96,
        0.06,
        badge_left,
        transform=ax0.transAxes,
        ha="right",
        va="bottom",
        fontsize=11.5,
        fontweight="bold",
        color=PALETTE["graphite"],
        bbox=dict(boxstyle="round,pad=0.55", fc=PALETTE["white"], ec=PALETTE["teal"], lw=1.5),
    )

    # --- Правая панель: Распределение остатков ---
    sns.histplot(
        residuals,
        kde=True,
        bins=14,
        ax=ax1,
        color=PALETTE["teal"],
        edgecolor=PALETTE["white"],
        linewidth=0.9,
        alpha=0.84,
        line_kws={"linewidth": 2.4, "color": PALETTE["graphite"]},
    )
    ax1.axvline(
        0.0,
        color=PALETTE["burgundy"],
        linestyle="--",
        linewidth=2.3,
        label="Нулевая ошибка (0 тыс. руб.)",
    )
    mean_err = float(np.mean(residuals))
    mean_err_str = f"{mean_err:+.1f}".replace(".", ",")
    ax1.axvline(
        mean_err,
        color=PALETTE["terracotta"],
        linestyle="-",
        linewidth=2.0,
        label=f"Среднее смещение: {mean_err_str} тыс. руб.",
    )

    style_axes(ax1, grid_axis="y")
    ax1.set_ylim(0, ax1.get_ylim()[1] * 1.25)
    ax1.set_title("Распределение ошибок прогноза (остатки)", fontsize=15.2, fontweight="bold", pad=12)
    ax1.set_xlabel("Ошибка прогноза: Факт − Прогноз (тыс. руб.)", fontsize=13.2, fontweight="bold")
    ax1.set_ylabel("Количество автомобилей (шт.)", fontsize=13.2, fontweight="bold")
    ax1.xaxis.set_major_formatter(krub_tick_formatter())
    ax1.legend(loc="upper left", frameon=True, facecolor=PALETTE["white"], fontsize=11.0)

    mae_str = f"{mae_krub:.1f}".replace(".", ",")
    rmse_str = f"{rmse_krub:.1f}".replace(".", ",")
    mape_str = f"{mape_pct:.2f}".replace(".", ",")
    metrics_card = (
        f"Метрики на тесте (n = {len(y_true)}):\n"
        f"MAE  = {mae_str} тыс. руб.\n"
        f"RMSE = {rmse_str} тыс. руб.\n"
        f"MAPE = {mape_str}%"
    )
    ax1.text(
        0.97,
        0.95,
        metrics_card,
        transform=ax1.transAxes,
        ha="right",
        va="top",
        fontsize=11.5,
        fontweight="bold",
        color=PALETTE["graphite"],
        bbox=dict(boxstyle="round,pad=0.55", fc=PALETTE["white"], ec=PALETTE["burgundy"], lw=1.5),
    )

    fig.suptitle(
        "Анализ точности и ошибок модели «Случайный лес» на отложенной выборке",
        fontsize=16.5,
        fontweight="bold",
        y=1.02,
    )
    plt.tight_layout()
    save_figure(fig, "residual_plots.png")


def _draw_box(
    ax: plt.Axes,
    x: float,
    y: float,
    w: float,
    h: float,
    title: str,
    body: str = "",
    fc: str = "#FFFFFF",
    ec: str = "#0F766E",
    lw: float = 2.0,
    ls: str = "-",
    title_color: str = "#1E293B",
    body_color: str = "#334155",
    title_size: float = 11.5,
    body_size: float = 9.8,
    rounding: float = 0.9,
    zorder: int = 3,
) -> None:
    """Рисует аккуратный скруглённый инженерный блок с заголовком и текстом."""
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle=f"round,pad=0.2,rounding_size={rounding}",
        facecolor=fc,
        edgecolor=ec,
        linewidth=lw,
        linestyle=ls,
        zorder=zorder,
    )
    ax.add_patch(patch)
    cx = x + w / 2.0
    if body:
        ax.text(
            cx,
            y + h * 0.78,
            title,
            ha="center",
            va="center",
            fontsize=title_size,
            fontweight="bold",
            color=title_color,
            zorder=zorder + 1,
        )
        ax.text(
            cx,
            y + h * 0.36,
            body,
            ha="center",
            va="center",
            fontsize=body_size,
            color=body_color,
            linespacing=1.32,
            zorder=zorder + 1,
        )
    else:
        ax.text(
            cx,
            y + h / 2.0,
            title,
            ha="center",
            va="center",
            fontsize=title_size,
            fontweight="bold",
            color=title_color,
            linespacing=1.25,
            zorder=zorder + 1,
        )


def _draw_arrow(
    ax: plt.Axes,
    start: tuple[float, float],
    end: tuple[float, float],
    color: str = "#1E293B",
    lw: float = 2.2,
    ls: str = "-",
    rad: float = 0.0,
    style: str = "-|>",
    mutation_scale: float = 16.0,
    zorder: int = 5,
) -> None:
    """Рисует чёткую векторную стрелку между блоками."""
    arrow = FancyArrowPatch(
        start,
        end,
        connectionstyle=f"arc3,rad={rad}",
        arrowstyle=style,
        mutation_scale=mutation_scale,
        color=color,
        linewidth=lw,
        linestyle=ls,
        zorder=zorder,
    )
    ax.add_patch(arrow)


def plot_system_block_diagram() -> None:
    """Переработанная 3-этапная структурная схема архитектуры программного комплекса."""
    configure_matplotlib()
    fig, ax = plt.subplots(figsize=(18.5, 10.6))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 62)
    ax.axis("off")
    fig.patch.set_facecolor(PALETTE["white"])

    # Заголовок схемы
    ax.text(
        50,
        59.6,
        "Структурная архитектура программного комплекса CarPrice Predictor ML (v2.2)",
        ha="center",
        va="center",
        fontsize=17.5,
        fontweight="bold",
        color=PALETTE["graphite"],
    )
    ax.text(
        50,
        56.9,
        "Проектирование и подготовка данных  →  Обучение и выгрузка моделей  →  Эксплуатация и логирование в SQLite",
        ha="center",
        va="center",
        fontsize=12.2,
        color=PALETTE["slate"],
        fontweight="bold",
    )

    # Контейнеры 3 этапов
    stages = [
        (
            1.2,
            30.2,
            "ЭТАП 1. ПРОЕКТИРОВАНИЕ\nИ ПОДГОТОВКА ДАННЫХ",
            "#F0FDFA",
            PALETTE["teal"],
            PALETTE["teal"],
        ),
        (
            34.9,
            30.2,
            "ЭТАП 2. ОБУЧЕНИЕ МОДЕЛЕЙ\nИ ВЫГРУЗКА АРТЕФАКТОВ",
            "#F8FAFC",
            PALETTE["graphite"],
            PALETTE["graphite"],
        ),
        (
            68.6,
            30.2,
            "ЭТАП 3. ПРОГРАММНЫЙ КОМПЛЕКС\n(ЭКСПЛУАТАЦИЯ)",
            "#FFF5F6",
            PALETTE["burgundy"],
            PALETTE["burgundy"],
        ),
    ]
    for sx, sw, header, bg_color, border_color, header_bg in stages:
        container = FancyBboxPatch(
            (sx, 2.2),
            sw,
            52.0,
            boxstyle="round,pad=0.25,rounding_size=1.3",
            facecolor=bg_color,
            edgecolor=border_color,
            linewidth=2.0,
            zorder=1,
        )
        ax.add_patch(container)
        banner = FancyBboxPatch(
            (sx, 48.2),
            sw,
            6.0,
            boxstyle="round,pad=0.25,rounding_size=1.1",
            facecolor=header_bg,
            edgecolor=header_bg,
            linewidth=1.5,
            zorder=2,
        )
        ax.add_patch(banner)
        ax.text(
            sx + sw / 2.0,
            51.2,
            header,
            ha="center",
            va="center",
            fontsize=11.8,
            fontweight="bold",
            color=PALETTE["white"],
            linespacing=1.22,
            zorder=3,
        )

    # ==================== ЭТАП 1 ====================
    _draw_box(
        ax,
        3.0,
        38.5,
        26.6,
        7.6,
        "1.1. Исходный датасет",
        "CarPrice_Assignment.csv\n205 автомобилей · 26 признаков",
        fc=PALETTE["white"],
        ec=PALETTE["teal"],
    )
    _draw_box(
        ax,
        3.0,
        26.0,
        26.6,
        10.0,
        "1.2. Очистка и инженерия признаков",
        "• Исправление марок (22 бренда)\n• Новые признаки (мощность/масса)\n• Пересчёт цен в рубли (× 93,5)",
        fc=PALETTE["white"],
        ec=PALETTE["teal"],
    )
    _draw_box(
        ax,
        3.0,
        14.2,
        26.6,
        9.4,
        "1.3. Кодирование и разбиение",
        "• OneHotEncoder + StandardScaler\n• Разбиение 80% / 20% (164 / 41)\n• Проверка входных диапазонов",
        fc=PALETTE["white"],
        ec=PALETTE["teal"],
    )
    _draw_box(
        ax,
        3.0,
        3.8,
        26.6,
        7.8,
        "Контрольный сценарий Loginom 7.4.2",
        "Независимая аналитическая модель\nдля перекрёстной проверки метрик",
        fc=PALETTE["rose_light"],
        ec=PALETTE["burgundy"],
        lw=1.9,
        ls="--",
        title_color=PALETTE["burgundy"],
    )

    _draw_arrow(ax, (16.3, 38.3), (16.3, 36.3), color=PALETTE["teal"])
    _draw_arrow(ax, (16.3, 25.8), (16.3, 23.9), color=PALETTE["teal"])
    _draw_arrow(ax, (16.3, 14.0), (16.3, 11.9), color=PALETTE["burgundy"], ls="--", lw=1.8)

    # ==================== ЭТАП 2 ====================
    _draw_box(
        ax,
        36.7,
        34.8,
        26.6,
        11.3,
        "2.1. Обучение 4 моделей (Python)",
        "• Случайный лес — R² = 0,9582 (лучшая)\n• Гребневая (Ridge) — R² = 0,8986\n• Нейросеть (MLP) — R² = 0,8537\n• Метод k-соседей (KNN) — R² = 0,7702",
        fc=PALETTE["white"],
        ec=PALETTE["graphite"],
    )
    _draw_box(
        ax,
        36.7,
        20.0,
        26.6,
        12.0,
        "2.2. Оценка качества и отбор",
        "• Расчёт R², MAE (тыс. ₽), RMSE, MAPE\n• Сверка результатов с Loginom 7.4.2\n• Расчёт σ остатков для 95% ДИ\n• Критерий приёмки: R² ≥ 0,90",
        fc=PALETTE["white"],
        ec=PALETTE["graphite"],
    )
    _draw_box(
        ax,
        36.7,
        3.8,
        26.6,
        13.2,
        "2.3. Версионирование v2.2 и выгрузка",
        "• models/model_*.joblib (4 модели)\n• models/preprocessor.joblib\n• reports/metrics.json (метрики)\n• models/metadata.json (метаданные)",
        fc=PALETTE["mint"],
        ec=PALETTE["teal"],
        lw=2.4,
        title_color=PALETTE["teal"],
    )

    _draw_arrow(ax, (50.0, 34.6), (50.0, 32.3), color=PALETTE["graphite"])
    _draw_arrow(ax, (50.0, 19.8), (50.0, 17.3), color=PALETTE["teal"], lw=2.4)

    # ==================== ЭТАП 3 ====================
    _draw_box(
        ax,
        70.4,
        33.8,
        26.6,
        12.3,
        "3.1. Сервис прогнозирования\n(ModelService)",
        "• Валидация-ограничитель ввода\n• Прогноз стоимости в рублях (₽)\n• 95% доверительный интервал\n• Вероятность цены в коридоре ±15%",
        fc=PALETTE["white"],
        ec=PALETTE["teal"],
        lw=2.3,
        title_color=PALETTE["teal"],
    )
    _draw_box(
        ax,
        70.4,
        17.6,
        12.6,
        12.8,
        "Веб-приложение\n(Streamlit)",
        "Калькулятор,\nOLAP-аналитика,\nпресеты авто,\nистория",
        fc=PALETTE["white"],
        ec=PALETTE["teal"],
        lw=2.0,
        title_size=10.6,
        body_size=9.3,
    )
    _draw_box(
        ax,
        84.4,
        17.6,
        12.6,
        12.8,
        "Telegram-бот\n(aiogram 3)",
        "Пошаговый FSM,\nпрогноз в ₽,\nбыстрые кнопки,\nQR-доступ",
        fc=PALETTE["white"],
        ec=PALETTE["soft_teal"],
        lw=2.0,
        title_size=10.6,
        body_size=9.3,
    )
    _draw_box(
        ax,
        70.4,
        3.8,
        26.6,
        10.2,
        "Локальная БД SQLite (predictions.db)",
        "Журнал логирования расчётов\n(дата, интерфейс, модель, параметры, прогноз ₽)",
        fc="#F1F5F9",
        ec=PALETTE["graphite"],
        lw=2.1,
        title_color=PALETTE["graphite"],
    )

    # Связи внутри Этапа 3
    _draw_arrow(ax, (76.7, 33.6), (76.7, 30.7), color=PALETTE["teal"], style="<|-|>", lw=2.0)
    _draw_arrow(ax, (90.7, 33.6), (90.7, 30.7), color=PALETTE["soft_teal"], style="<|-|>", lw=2.0)
    _draw_arrow(ax, (76.7, 17.4), (76.7, 14.3), color=PALETTE["graphite"], lw=1.9)
    _draw_arrow(ax, (90.7, 17.4), (90.7, 14.3), color=PALETTE["graphite"], lw=1.9)

    ax.text(
        83.7,
        15.8,
        "логирование расчётов",
        ha="center",
        va="center",
        fontsize=9.2,
        fontweight="bold",
        color=PALETTE["slate"],
        bbox=dict(boxstyle="round,pad=0.2", fc="#FFF5F6", ec="none"),
        zorder=6,
    )

    # ==================== МЕЖЭТАПНЫЕ СТРЕЛКИ ====================
    # Из 1.3 (кодирование) -> в 2.1 (обучение)
    _draw_arrow(
        ax,
        (29.8, 21.0),
        (36.5, 40.5),
        color=PALETTE["teal"],
        lw=2.6,
        rad=-0.12,
        mutation_scale=18,
    )
    # Из Loginom (Этап 1) -> в 2.2 (сверка)
    _draw_arrow(
        ax,
        (29.8, 7.8),
        (36.5, 25.0),
        color=PALETTE["burgundy"],
        lw=2.1,
        ls="--",
        rad=-0.12,
        mutation_scale=16,
    )
    # Из 2.3 (выгрузка v2.2) -> в 3.1 (ModelService)
    _draw_arrow(
        ax,
        (63.5, 11.0),
        (70.2, 40.0),
        color=PALETTE["burgundy"],
        lw=2.8,
        rad=-0.14,
        mutation_scale=19,
    )
    ax.text(
        66.9,
        26.5,
        "выгрузка\n.joblib",
        ha="center",
        va="center",
        fontsize=9.5,
        fontweight="bold",
        color=PALETTE["burgundy"],
        bbox=dict(boxstyle="round,pad=0.25", fc=PALETTE["white"], ec=PALETTE["burgundy"], lw=1.0),
        zorder=7,
    )

    plt.tight_layout()
    save_figure(fig, "system_block_diagram.png")


def _draw_gost_terminator(ax: plt.Axes, cx: float, cy: float, w: float, h: float, text: str) -> None:
    """Блок ГОСТ «Терминатор» (Начало / Конец)."""
    patch = FancyBboxPatch(
        (cx - w / 2, cy - h / 2),
        w,
        h,
        boxstyle=f"round,pad=0.1,rounding_size={h / 2}",
        facecolor=PALETTE["graphite"],
        edgecolor=PALETTE["graphite"],
        linewidth=2.0,
        zorder=3,
    )
    ax.add_patch(patch)
    ax.text(cx, cy, text, ha="center", va="center", fontsize=12.5, fontweight="bold", color=PALETTE["white"], zorder=4)


def _draw_gost_process(
    ax: plt.Axes,
    cx: float,
    cy: float,
    w: float,
    h: float,
    title: str,
    subtitle: str,
    ec: str = "#0F766E",
    fc: str = "#FFFFFF",
) -> None:
    """Блок ГОСТ «Процесс» (прямоугольник)."""
    patch = FancyBboxPatch(
        (cx - w / 2, cy - h / 2),
        w,
        h,
        boxstyle="square,pad=0.0",
        facecolor=fc,
        edgecolor=ec,
        linewidth=2.1,
        zorder=3,
    )
    ax.add_patch(patch)
    ax.text(cx, cy + h * 0.21, title, ha="center", va="center", fontsize=11.3, fontweight="bold", color=PALETTE["graphite"], zorder=4)
    ax.text(cx, cy - h * 0.20, subtitle, ha="center", va="center", fontsize=9.8, color=PALETTE["slate"], linespacing=1.22, zorder=4)


def _draw_gost_io(
    ax: plt.Axes,
    cx: float,
    cy: float,
    w: float,
    h: float,
    title: str,
    subtitle: str,
    ec: str = "#0F766E",
    fc: str = "#F0FDFA",
) -> None:
    """Блок ГОСТ «Ввод / Вывод» (параллелограмм)."""
    skew = 2.1
    pts = [
        (cx - w / 2 + skew, cy + h / 2),
        (cx + w / 2 + skew * 0.4, cy + h / 2),
        (cx + w / 2 - skew, cy - h / 2),
        (cx - w / 2 - skew * 0.4, cy - h / 2),
    ]
    poly = Polygon(pts, closed=True, facecolor=fc, edgecolor=ec, linewidth=2.1, zorder=3)
    ax.add_patch(poly)
    ax.text(cx, cy + h * 0.20, title, ha="center", va="center", fontsize=11.2, fontweight="bold", color=PALETTE["teal"], zorder=4)
    ax.text(cx, cy - h * 0.20, subtitle, ha="center", va="center", fontsize=9.7, color=PALETTE["graphite"], linespacing=1.2, zorder=4)


def _draw_gost_decision(ax: plt.Axes, cx: float, cy: float, w: float, h: float, text: str) -> None:
    """Блок ГОСТ «Решение» (ромб)."""
    pts = [
        (cx, cy + h / 2),
        (cx + w / 2, cy),
        (cx, cy - h / 2),
        (cx - w / 2, cy),
    ]
    poly = Polygon(pts, closed=True, facecolor=PALETTE["rose_light"], edgecolor=PALETTE["burgundy"], linewidth=2.2, zorder=3)
    ax.add_patch(poly)
    ax.text(cx, cy, text, ha="center", va="center", fontsize=10.8, fontweight="bold", color=PALETTE["burgundy"], linespacing=1.2, zorder=4)


def plot_flowchart_algorithm() -> None:
    """Переработанная ГОСТ-блок-схема алгоритма обучения и эксплуатации системы."""
    configure_matplotlib()
    fig, ax = plt.subplots(figsize=(17.2, 12.6))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 76)
    ax.axis("off")
    fig.patch.set_facecolor(PALETTE["white"])

    # Заголовок
    ax.text(
        50,
        73.8,
        "Блок-схема алгоритма работы программного комплекса CarPrice Predictor ML",
        ha="center",
        va="center",
        fontsize=17,
        fontweight="bold",
        color=PALETTE["graphite"],
    )

    # Две колонки-подложки (Фаза 1: Обучение и выгрузка | Фаза 2: Эксплуатация)
    for x0, w, label, hdr_c, bg_c in [
        (2.0, 44.5, "ФАЗА 1. ПОДГОТОВКА ДАННЫХ, ОБУЧЕНИЕ И ВЫГРУЗКА (v2.2)", PALETTE["teal"], "#F8FAFC"),
        (53.5, 44.5, "ФАЗА 2. ИНФЕРЕНС, ИНТЕРФЕЙСЫ И ЛОГИРОВАНИЕ В SQLITE", PALETTE["burgundy"], "#FDF8F8"),
    ]:
        panel = FancyBboxPatch(
            (x0, 1.5),
            w,
            69.0,
            boxstyle="round,pad=0.2,rounding_size=1.2",
            facecolor=bg_c,
            edgecolor=hdr_c,
            linewidth=1.6,
            zorder=1,
        )
        ax.add_patch(panel)
        hdr = FancyBboxPatch(
            (x0, 66.5),
            w,
            4.0,
            boxstyle="round,pad=0.2,rounding_size=0.9",
            facecolor=hdr_c,
            edgecolor=hdr_c,
            linewidth=1.2,
            zorder=2,
        )
        ax.add_patch(hdr)
        ax.text(x0 + w / 2, 68.5, label, ha="center", va="center", fontsize=10.8, fontweight="bold", color=PALETTE["white"], zorder=3)

    # ==================== ЛЕВАЯ КОЛОНКА (cx = 26.5) ====================
    lx = 26.5
    bw = 30.5

    _draw_gost_terminator(ax, lx, 62.2, 16.0, 4.4, "НАЧАЛО")
    _draw_gost_process(
        ax,
        lx,
        52.6,
        bw,
        6.8,
        "1. Загрузка и очистка данных",
        "205 авто, очистка 22 марок,\nинженерия признаков, пересчёт в ₽",
    )
    _draw_gost_process(
        ax,
        lx,
        42.3,
        bw,
        6.8,
        "2. Разбиение 80% / 20% и масштаб",
        "Обучение: 164 авто | Тест: 41 авто\nOneHotEncoder + StandardScaler",
    )
    _draw_gost_process(
        ax,
        lx,
        32.0,
        bw,
        6.8,
        "3. Обучение 4 моделей регрессии",
        "Random Forest, Ridge, MLP, KNN\nРасчёт R², MAE, RMSE, MAPE",
    )
    _draw_gost_decision(
        ax,
        lx,
        19.6,
        29.0,
        9.4,
        "Критерий качества\nR² ≥ 0,90 выполнен?",
    )
    _draw_gost_io(
        ax,
        lx,
        6.8,
        29.5,
        6.8,
        "4. Выгрузка артефактов v2.2",
        "models/*.joblib, preprocessor.joblib,\nmetrics.json, metadata.json",
    )

    # Вертикальные стрелки левой колонки
    _draw_arrow(ax, (lx, 59.9), (lx, 56.2), color=PALETTE["graphite"])
    _draw_arrow(ax, (lx, 49.1), (lx, 45.9), color=PALETTE["graphite"])
    _draw_arrow(ax, (lx, 38.8), (lx, 35.6), color=PALETTE["graphite"])
    _draw_arrow(ax, (lx, 28.5), (lx, 24.5), color=PALETTE["graphite"])
    _draw_arrow(ax, (lx, 14.8), (lx, 10.4), color=PALETTE["teal"], lw=2.3)
    ax.text(lx + 2.4, 12.8, "Да", fontsize=11, fontweight="bold", color=PALETTE["teal"])

    # Цикл «Нет» (подбор гиперпараметров) слева от ромба
    ax.plot([lx - 14.5, 5.2, 5.2], [19.6, 19.6, 32.0], color=PALETTE["burgundy"], linewidth=2.0, zorder=4)
    _draw_arrow(ax, (5.2, 32.0), (lx - bw / 2 - 0.2, 32.0), color=PALETTE["burgundy"], lw=2.0)
    ax.text(
        5.5,
        25.8,
        "Нет\n(подбор\nпарам.)",
        ha="left",
        va="center",
        fontsize=9.3,
        fontweight="bold",
        color=PALETTE["burgundy"],
        bbox=dict(boxstyle="round,pad=0.22", fc=PALETTE["white"], ec=PALETTE["burgundy"], lw=0.9),
        zorder=6,
    )

    # ==================== ПРАВАЯ КОЛОНКА (cx = 73.5) ====================
    rx = 73.5

    _draw_gost_io(
        ax,
        rx,
        60.8,
        29.5,
        6.8,
        "5. Ввод параметров автомобиля",
        "Веб-приложение (Streamlit) или\nTelegram-бот (aiogram 3)",
        ec=PALETTE["teal"],
    )
    _draw_gost_decision(
        ax,
        rx,
        48.0,
        29.5,
        9.4,
        "Ограничитель ввода:\nзначения в норме?",
    )
    _draw_gost_process(
        ax,
        rx,
        35.0,
        bw,
        7.2,
        "6. Инференс (ModelService)",
        "Прогноз цены в ₽ (×93,5), 95% ДИ\nи вероятность в коридоре ±15%",
        ec=PALETTE["teal"],
    )
    _draw_gost_process(
        ax,
        rx,
        24.2,
        bw,
        6.6,
        "7. Логирование в SQLite",
        "Запись параметров, модели и цены\nв локальную БД predictions.db",
        ec=PALETTE["graphite"],
        fc="#F1F5F9",
    )
    _draw_gost_io(
        ax,
        rx,
        13.6,
        29.5,
        6.6,
        "8. Вывод отчёта пользователю",
        "Рыночная цена (₽), сегмент,\n95% интервал и вероятность",
        ec=PALETTE["teal"],
    )
    _draw_gost_terminator(ax, rx, 5.2, 16.0, 4.4, "КОНЕЦ")

    # Вертикальные стрелки правой колонки
    _draw_arrow(ax, (rx, 57.3), (rx, 52.9), color=PALETTE["graphite"])
    _draw_arrow(ax, (rx, 43.2), (rx, 38.8), color=PALETTE["teal"], lw=2.3)
    ax.text(rx + 2.4, 41.0, "Да", fontsize=11, fontweight="bold", color=PALETTE["teal"])
    _draw_arrow(ax, (rx, 31.3), (rx, 27.7), color=PALETTE["graphite"])
    _draw_arrow(ax, (rx, 20.8), (rx, 17.1), color=PALETTE["graphite"])
    _draw_arrow(ax, (rx, 10.2), (rx, 7.6), color=PALETTE["graphite"])

    # Цикл «Нет» (ограничитель диапазонов) справа от ромба
    ax.plot([rx + 14.75, 95.3, 95.3], [48.0, 48.0, 60.8], color=PALETTE["burgundy"], linewidth=2.0, zorder=4)
    _draw_arrow(ax, (95.3, 60.8), (rx + 15.6, 60.8), color=PALETTE["burgundy"], lw=2.0)
    ax.text(
        94.9,
        54.4,
        "Нет\n(коррекция)",
        ha="right",
        va="center",
        fontsize=9.3,
        fontweight="bold",
        color=PALETTE["burgundy"],
        bbox=dict(boxstyle="round,pad=0.22", fc=PALETTE["white"], ec=PALETTE["burgundy"], lw=0.9),
        zorder=6,
    )

    # Переход от Фазы 1 (Выгрузка артефактов) к Фазе 2 (Ввод параметров)
    ax.plot([lx + 15.2, 50.0, 50.0], [6.8, 6.8, 60.8], color=PALETTE["teal"], linewidth=2.6, zorder=4)
    _draw_arrow(ax, (50.0, 60.8), (rx - 15.2, 60.8), color=PALETTE["teal"], lw=2.6, mutation_scale=18)
    ax.text(
        50.0,
        34.5,
        "Загрузка\nмоделей\nv2.2",
        ha="center",
        va="center",
        fontsize=9.8,
        fontweight="bold",
        color=PALETTE["teal"],
        bbox=dict(boxstyle="round,pad=0.35", fc=PALETTE["mint"], ec=PALETTE["teal"], lw=1.4),
        zorder=6,
    )

    plt.tight_layout()
    save_figure(fig, "flowchart_algorithm.png")


def generate_bot_qr_code() -> None:
    """Генерация высококонтрастного QR-кода Telegram-бота @testcursomsskm_bot."""
    configure_matplotlib()
    url = "https://t.me/testcursomsskm_bot"

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=18,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color=PALETTE["graphite"], back_color=PALETTE["white"]).convert("RGB")
    qr_arr = np.asarray(qr_img)

    fig = plt.figure(figsize=(6.0, 7.3), facecolor=PALETTE["white"])
    ax_frame = fig.add_axes([0.02, 0.02, 0.96, 0.96])
    ax_frame.set_xlim(0, 100)
    ax_frame.set_ylim(0, 122)
    ax_frame.axis("off")

    # Внешняя карточка с изумрудно-бирюзовой рамкой
    outer = FancyBboxPatch(
        (2.5, 2.5),
        95.0,
        117.0,
        boxstyle="round,pad=0.3,rounding_size=4.5",
        facecolor=PALETTE["white"],
        edgecolor=PALETTE["teal"],
        linewidth=4.0,
        zorder=1,
    )
    ax_frame.add_patch(outer)

    # Верхняя акцентная плашка
    top_bar = FancyBboxPatch(
        (16.0, 108.0),
        68.0,
        7.5,
        boxstyle="round,pad=0.2,rounding_size=3.0",
        facecolor=PALETTE["teal"],
        edgecolor=PALETTE["teal"],
        linewidth=1.0,
        zorder=2,
    )
    ax_frame.add_patch(top_bar)
    ax_frame.text(
        50.0,
        111.75,
        "TELEGRAM-БОТ ОЦЕНКИ АВТО",
        ha="center",
        va="center",
        fontsize=11.5,
        fontweight="bold",
        color=PALETTE["white"],
        zorder=3,
    )

    # Подписи внизу карточки
    ax_frame.text(
        50.0,
        17.5,
        "@testcursomsskm_bot",
        ha="center",
        va="center",
        fontsize=17,
        fontweight="bold",
        color=PALETTE["teal"],
        zorder=3,
    )
    ax_frame.text(
        50.0,
        10.8,
        "Telegram-бот CarPrice Predictor",
        ha="center",
        va="center",
        fontsize=13,
        fontweight="bold",
        color=PALETTE["graphite"],
        zorder=3,
    )
    ax_frame.text(
        50.0,
        5.8,
        "Наведите камеру смартфона для запуска расчёта",
        ha="center",
        va="center",
        fontsize=10.2,
        color=PALETTE["slate"],
        zorder=3,
    )

    # Размещение QR-кода по центру карточки
    ax_qr = fig.add_axes([0.14, 0.23, 0.72, 0.62])
    ax_qr.imshow(qr_arr, interpolation="nearest")
    ax_qr.axis("off")

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    for out_dir in (FIGURES_DIR, SCREENSHOTS_DIR):
        fig.savefig(
            out_dir / "bot_qr_code.png",
            dpi=300,
            bbox_inches="tight",
            facecolor=PALETTE["white"],
            pad_inches=0.12,
        )
    plt.close(fig)


def main() -> None:
    """Точка входа: регенерация всех 12 графиков, схем и QR-кода."""
    print("Загрузка и очистка датасета CarPrice_Assignment.csv...")
    df_raw = load_raw_data()
    df_clean = clean_car_dataframe(df_raw)

    print("1/7 Генерация базовых EDA/OLAP графиков и сравнения с Loginom...")
    generate_all_eda_visualizations(df_clean)

    print("2/7 Генерация olap_drive_price.png...")
    plot_olap_drive_price(df_clean)

    print("3/7 Генерация feature_importance.png...")
    plot_feature_importance()

    print("4/7 Генерация residual_plots.png...")
    plot_residual_analysis(df_clean)

    print("5/7 Генерация system_block_diagram.png...")
    plot_system_block_diagram()

    print("6/7 Генерация flowchart_algorithm.png...")
    plot_flowchart_algorithm()

    print("7/7 Генерация bot_qr_code.png...")
    generate_bot_qr_code()

    expected_files: List[str] = [
        "price_distribution.png",
        "brand_vs_price.png",
        "correlation_heatmap.png",
        "olap_body_fuel_price.png",
        "olap_engine_horsepower.png",
        "model_comparison_metrics.png",
        "olap_drive_price.png",
        "feature_importance.png",
        "residual_plots.png",
        "system_block_diagram.png",
        "flowchart_algorithm.png",
        "bot_qr_code.png",
    ]

    print("\nГотово! Проверенные файлы в reports/figures/ и screenshots/:")
    for name in expected_files:
        p1 = FIGURES_DIR / name
        p2 = SCREENSHOTS_DIR / name
        s1 = p1.stat().st_size if p1.exists() else 0
        s2 = p2.stat().st_size if p2.exists() else 0
        print(f"  {name:30s} | figures: {s1:8d} B | screenshots: {s2:8d} B")


if __name__ == "__main__":
    main()
