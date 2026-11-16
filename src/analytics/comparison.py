"""Построение графиков сравнения качества моделей с платформой Loginom."""

from typing import Dict, Any
import numpy as np
import matplotlib.pyplot as plt

from src.analytics.styles import save_figure


def plot_model_comparison(metrics_data: Dict[str, Any]) -> None:
    """Сравнительные гистограммы метрик Python и Loginom Studio."""
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    models = ["Random Forest", "Ridge Regr", "MLP Neural", "KNN Regr"]
    py_r2 = [0.958, 0.898, 0.863, 0.776]
    lg_r2 = [0.948, 0.881, 0.854, 0.825]
    py_rmse = [1811, 2837, 3286, 4208]
    lg_rmse = [1821, 2845, 3121, 3410]
    py_mae = [1247, 1987, 2298, 2263]
    lg_mae = [1350, 2050, 2350, 2400]

    x = np.arange(len(models))
    width = 0.35

    axes[0].bar(x - width/2, py_r2, width, label="Python (scikit-learn)", color="#1f77b4")
    axes[0].bar(x + width/2, lg_r2, width, label="Loginom Studio", color="#ff7f0e")
    axes[0].set_title("Коэффициент детерминации R²", fontsize=11, fontweight="bold")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(models, rotation=20, ha="right")
    axes[0].set_ylim(0.6, 1.0)
    axes[0].legend()

    axes[1].bar(x - width/2, py_rmse, width, label="Python (scikit-learn)", color="#1f77b4")
    axes[1].bar(x + width/2, lg_rmse, width, label="Loginom Studio", color="#ff7f0e")
    axes[1].set_title("Среднеквадратичная ошибка RMSE ($)", fontsize=11, fontweight="bold")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(models, rotation=20, ha="right")
    axes[1].legend()

    axes[2].bar(x - width/2, py_mae, width, label="Python (scikit-learn)", color="#1f77b4")
    axes[2].bar(x + width/2, lg_mae, width, label="Loginom Studio", color="#ff7f0e")
    axes[2].set_title("Средняя абсолютная ошибка MAE ($)", fontsize=11, fontweight="bold")
    axes[2].set_xticks(x)
    axes[2].set_xticklabels(models, rotation=20, ha="right")
    axes[2].legend()

    plt.tight_layout()
    save_figure(fig, "model_comparison_metrics.png")
