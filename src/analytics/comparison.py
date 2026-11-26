"""Построение графиков сравнения качества моделей Python (scikit-learn) и Loginom 7.4.2."""

import json
from typing import Dict, Any, List, Tuple
import numpy as np
import matplotlib.pyplot as plt

from src.config import METRICS_PATH, USD_TO_RUB_RATE
from src.analytics.styles import (
    PALETTE,
    configure_matplotlib,
    format_thousands,
    style_axes,
    save_figure,
)

MODEL_ORDER: List[Tuple[str, str]] = [
    ("random_forest", "Случайный\nлес"),
    ("linear_regression", "Гребневая\n(Ridge)"),
    ("neural_network", "Нейросеть\n(MLP)"),
    ("knn", "k-соседей\n(KNN)"),
]


def _load_metrics(metrics_data: Dict[str, Any]) -> Dict[str, Any]:
    """Возвращает переданные метрики или загружает актуальные из reports/metrics.json."""
    if metrics_data and "random_forest" in metrics_data:
        return metrics_data
    if METRICS_PATH.exists():
        with open(METRICS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def plot_model_comparison(metrics_data: Dict[str, Any]) -> None:
    """Сравнительные диаграммы качества 4 моделей: Python (scikit-learn) vs Loginom 7.4.2."""
    configure_matplotlib()
    data = _load_metrics(metrics_data)

    labels = [label for _, label in MODEL_ORDER]
    py_r2, lg_r2 = [], []
    py_mae_krub, lg_mae_krub = [], []
    py_mape, lg_mape = [], []

    for key, _ in MODEL_ORDER:
        entry = data.get(key, {})
        test = entry.get("test", {})
        lg = entry.get("loginom_benchmark", {})

        py_r2.append(float(test.get("r2", 0.0)))
        lg_r2.append(float(lg.get("r2_test", lg.get("r2", 0.0))))

        py_mae_krub.append(float(test.get("mae", 0.0)) * USD_TO_RUB_RATE / 1000.0)
        lg_mae_krub.append(float(lg.get("mae_test", lg.get("mae", 0.0))) * USD_TO_RUB_RATE / 1000.0)

        py_mape.append(float(test.get("mape", 0.0)))
        lg_mape.append(float(lg.get("mape_test", lg.get("mape", 0.0))))

    fig, axes = plt.subplots(1, 3, figsize=(18.0, 6.6))
    x = np.arange(len(labels))
    width = 0.36
    gap = 0.02

    # --- Панель 1: R² (тест) ---
    ax0 = axes[0]
    b0_py = ax0.bar(x - width / 2 - gap, py_r2, width, label="Python (scikit-learn)", color=PALETTE["teal"])
    b0_lg = ax0.bar(x + width / 2 + gap, lg_r2, width, label="Loginom 7.4.2", color=PALETTE["burgundy"])
    ax0.axhline(
        0.90,
        color=PALETTE["terracotta"],
        linestyle="--",
        linewidth=1.8,
        zorder=2,
        label="Целевой порог (0,90)",
    )
    style_axes(ax0, grid_axis="y")
    ax0.set_title("Коэффициент R² (тест)\n↑ выше — лучше", fontsize=14.5, fontweight="bold", pad=10)
    ax0.set_xticks(x)
    ax0.set_xticklabels(labels, fontsize=11.5, fontweight="bold")
    ax0.set_ylabel("Коэффициент детерминации R²", fontsize=12.5, fontweight="bold")
    ax0.set_ylim(0.65, 1.06)
    for bars, color in [(b0_py, PALETTE["teal"]), (b0_lg, PALETTE["burgundy"])]:
        for bar in bars:
            h = bar.get_height()
            ax0.text(
                bar.get_x() + bar.get_width() / 2,
                h + 0.008,
                f"{h:.3f}".replace(".", ","),
                ha="center",
                va="bottom",
                fontsize=9.6,
                fontweight="bold",
                color=color,
                bbox=dict(boxstyle="round,pad=0.10", fc=PALETTE["surface"], ec="none", alpha=0.88),
                zorder=5,
            )

    # --- Панель 2: MAE (тыс. руб.) ---
    ax1 = axes[1]
    b1_py = ax1.bar(x - width / 2 - gap, py_mae_krub, width, label="Python (scikit-learn)", color=PALETTE["teal"])
    b1_lg = ax1.bar(x + width / 2 + gap, lg_mae_krub, width, label="Loginom 7.4.2", color=PALETTE["burgundy"])
    style_axes(ax1, grid_axis="y")
    ax1.set_title("Средняя ошибка MAE (тыс. руб.)\n↓ ниже — лучше", fontsize=14.5, fontweight="bold", pad=10)
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, fontsize=11.5, fontweight="bold")
    ax1.set_ylabel("MAE (тыс. руб.)", fontsize=12.5, fontweight="bold")
    max_mae = max(max(py_mae_krub), max(lg_mae_krub), 1.0)
    ax1.set_ylim(0, max_mae * 1.22)
    for bars, color in [(b1_py, PALETTE["teal"]), (b1_lg, PALETTE["burgundy"])]:
        for bar in bars:
            h = bar.get_height()
            ax1.text(
                bar.get_x() + bar.get_width() / 2,
                h + max_mae * 0.02,
                format_thousands(h, 0),
                ha="center",
                va="bottom",
                fontsize=10.8,
                fontweight="bold",
                color=color,
            )

    # --- Панель 3: MAPE (%) ---
    ax2 = axes[2]
    b2_py = ax2.bar(x - width / 2 - gap, py_mape, width, label="Python (scikit-learn)", color=PALETTE["teal"])
    b2_lg = ax2.bar(x + width / 2 + gap, lg_mape, width, label="Loginom 7.4.2", color=PALETTE["burgundy"])
    style_axes(ax2, grid_axis="y")
    ax2.set_title("Относительная ошибка MAPE (%)\n↓ ниже — лучше", fontsize=14.5, fontweight="bold", pad=10)
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels, fontsize=11.5, fontweight="bold")
    ax2.set_ylabel("MAPE (%)", fontsize=12.5, fontweight="bold")
    max_mape = max(max(py_mape), max(lg_mape), 1.0)
    ax2.set_ylim(0, max_mape * 1.22)
    for bars, color in [(b2_py, PALETTE["teal"]), (b2_lg, PALETTE["burgundy"])]:
        for bar in bars:
            h = bar.get_height()
            ax2.text(
                bar.get_x() + bar.get_width() / 2,
                h + max_mape * 0.02,
                f"{h:.1f}%".replace(".", ","),
                ha="center",
                va="bottom",
                fontsize=10.5,
                fontweight="bold",
                color=color,
            )

    # Общая крупная легенда сверху под общим заголовком
    handles, legend_labels = ax0.get_legend_handles_labels()
    fig.legend(
        handles,
        legend_labels,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.965),
        ncol=3,
        frameon=True,
        facecolor=PALETTE["white"],
        fontsize=12.5,
    )
    fig.suptitle(
        "Сравнение качества моделей машинного обучения: Python (scikit-learn) vs Loginom 7.4.2",
        fontsize=16.5,
        fontweight="bold",
        y=1.03,
    )
    plt.tight_layout(rect=[0, 0, 1, 0.90])
    save_figure(fig, "model_comparison_metrics.png")
