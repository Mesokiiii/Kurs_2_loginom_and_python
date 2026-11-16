"""Настройки стиля и сохранение графиков."""

import logging
from pathlib import Path
import matplotlib.pyplot as plt

from src.config import FIGURES_DIR, SCREENSHOTS_DIR

logger = logging.getLogger(__name__)

# Академический стиль оформления графиков
plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Segoe UI"]
plt.rcParams["axes.edgecolor"] = "#cccccc"
plt.rcParams["axes.linewidth"] = 0.8


def save_figure(fig: plt.Figure, filename: str) -> None:
    """Сохранение графика в figures/ и screenshots/ в высоком разрешении 300 DPI."""
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    path_fig = FIGURES_DIR / filename
    path_scr = SCREENSHOTS_DIR / filename

    fig.savefig(path_fig, dpi=300, bbox_inches="tight")
    fig.savefig(path_scr, dpi=300, bbox_inches="tight")
    plt.close(fig)
    logger.info("График сохранен: %s", filename)
