"""Настройки стиля, академической палитры и сохранения графиков."""

import logging
import shutil
from typing import Union
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.ticker import FuncFormatter

from src.config import FIGURES_DIR, SCREENSHOTS_DIR, USD_TO_RUB_RATE

logger = logging.getLogger(__name__)

# Строгая академическая инженерная палитра (графит, изумрудно-бирюзовый, бордовый, терракота)
PALETTE = {
    "graphite": "#1E293B",      # Глубокий графит (заголовки, текст, рамки)
    "teal": "#0F766E",          # Изумрудно-бирюзовый (основной акцент, Python)
    "soft_teal": "#14B8A6",     # Мягкий бирюзовый (дополнительный акцент, коридоры)
    "mint": "#CCFBF1",          # Светло-мятный (фоновая подсветка)
    "burgundy": "#9F1239",      # Бордовый / малиновый (Loginom, среднее, выделения)
    "terracotta": "#C2410C",    # Тёплая терракота (медиана, пороговые линии)
    "rose_light": "#FFE4E6",    # Мягкий светло-розовый (акцентные подложки)
    "slate": "#64748B",         # Грифельно-серый (подписи, вспомогательные элементы)
    "grid": "#CBD5E1",          # Светлая сетка
    "surface": "#F8FAFC",       # Светлая поверхность области графика
    "white": "#FFFFFF",         # Чистый белый фон
}

# Расходящаяся цветовая карта: бордовый (-1) -> светлый (0) -> изумрудно-бирюзовый (+1)
TEAL_BURGUNDY_CMAP = LinearSegmentedColormap.from_list(
    "teal_burgundy_div",
    ["#9F1239", "#E11D48", "#F8FAFC", "#14B8A6", "#0F766E"],
)

# Последовательная бирюзовая карта (для тепловых OLAP-матриц)
TEAL_SEQ_CMAP = LinearSegmentedColormap.from_list(
    "mint_to_teal",
    ["#F0FDFA", "#99F6E4", "#14B8A6", "#0F766E", "#134E4A"],
)

# Последовательная карта цен: мягкий бирюзовый -> глубокий изумруд -> терракота -> бордовый
PRICE_CMAP = LinearSegmentedColormap.from_list(
    "price_teal_burgundy",
    ["#99F6E4", "#14B8A6", "#0F766E", "#C2410C", "#9F1239", "#4C0519"],
)

# Словари перевода признаков и категорий на понятный русский язык
FEATURE_RU_NAMES = {
    "enginesize": "Объём двигателя",
    "curbweight": "Снаряжённая масса",
    "horsepower": "Мощность (л.с.)",
    "carwidth": "Ширина кузова",
    "carlength": "Длина кузова",
    "wheelbase": "Колёсная база",
    "boreratio": "Диаметр цилиндра",
    "citympg": "Расход город",
    "highwaympg": "Расход трасса",
    "price": "Цена (руб.)",
    "engine_to_weight": "Отношение объёма к массе",
    "power_to_weight": "Удельная мощность",
    "peakrpm": "Макс. обороты двигателя",
    "stroke": "Ход поршня",
    "compressionratio": "Степень сжатия",
    "carheight": "Высота кузова",
    "symboling": "Страховой рейтинг",
    "cylindernumber": "Число цилиндров",
    "doornumber": "Число дверей",
}

BODY_RU_NAMES = {
    "hardtop": "Хардтоп",
    "convertible": "Кабриолет",
    "sedan": "Седан",
    "wagon": "Универсал",
    "hatchback": "Хэтчбек",
}

FUEL_RU_NAMES = {
    "gas": "Бензин",
    "diesel": "Дизель",
}

DRIVE_RU_NAMES = {
    "rwd": "Задний привод (RWD)",
    "fwd": "Передний привод (FWD)",
    "4wd": "Полный привод (4WD)",
}

BRAND_DISPLAY_NAMES = {
    "alfa-romeo": "Alfa Romeo",
    "audi": "Audi",
    "bmw": "BMW",
    "buick": "Buick",
    "chevrolet": "Chevrolet",
    "dodge": "Dodge",
    "honda": "Honda",
    "isuzu": "Isuzu",
    "jaguar": "Jaguar",
    "mazda": "Mazda",
    "mercury": "Mercury",
    "mitsubishi": "Mitsubishi",
    "nissan": "Nissan",
    "peugeot": "Peugeot",
    "plymouth": "Plymouth",
    "porsche": "Porsche",
    "renault": "Renault",
    "saab": "Saab",
    "subaru": "Subaru",
    "toyota": "Toyota",
    "volkswagen": "Volkswagen",
    "volvo": "Volvo",
}


def configure_matplotlib() -> None:
    """Настройка глобальных параметров Matplotlib для презентационной читаемости."""
    plt.style.use(
        "seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default"
    )
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["DejaVu Sans", "Arial", "Segoe UI"],
        "axes.unicode_minus": False,
        "figure.facecolor": PALETTE["white"],
        "axes.facecolor": PALETTE["surface"],
        "axes.edgecolor": PALETTE["grid"],
        "axes.linewidth": 1.0,
        "axes.titlesize": 16,
        "axes.titleweight": "bold",
        "axes.titlecolor": PALETTE["graphite"],
        "axes.labelsize": 13.5,
        "axes.labelweight": "bold",
        "axes.labelcolor": PALETTE["graphite"],
        "text.color": PALETTE["graphite"],
        "xtick.color": PALETTE["graphite"],
        "ytick.color": PALETTE["graphite"],
        "xtick.labelsize": 11.5,
        "ytick.labelsize": 11.5,
        "legend.fontsize": 11.5,
        "legend.title_fontsize": 12,
        "legend.framealpha": 0.95,
        "legend.edgecolor": PALETTE["grid"],
        "grid.color": PALETTE["grid"],
        "grid.linestyle": "--",
        "grid.linewidth": 0.7,
        "grid.alpha": 0.65,
    })


configure_matplotlib()


def usd_to_krub(values: Union[float, int, np.ndarray, pd.Series]) -> Union[float, np.ndarray, pd.Series]:
    """Перевод стоимости из USD в тысячи рублей по курсу проекта (USD_TO_RUB_RATE)."""
    return values * USD_TO_RUB_RATE / 1000.0


def format_thousands(val: float, decimals: int = 0) -> str:
    """Форматирование числа с пробелом в качестве разделителя тысяч и запятой для дроби."""
    if decimals == 0:
        return f"{val:,.0f}".replace(",", " ")
    formatted = f"{val:,.{decimals}f}".replace(",", " ").replace(".", ",")
    return formatted


def krub_tick_formatter() -> FuncFormatter:
    """Форматтер осей для значений в тыс. руб. с пробелами между разрядами."""
    return FuncFormatter(lambda x, _: format_thousands(x, 0))


def style_axes(ax: plt.Axes, grid_axis: str = "y") -> None:
    """Единое аккуратное оформление осей графика."""
    ax.set_facecolor(PALETTE["surface"])
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(PALETTE["slate"])
    ax.spines["bottom"].set_color(PALETTE["slate"])
    ax.spines["left"].set_linewidth(1.0)
    ax.spines["bottom"].set_linewidth(1.0)
    ax.grid(True, axis=grid_axis, linestyle="--", alpha=0.55, color=PALETTE["grid"])
    ax.set_axisbelow(True)


def save_figure(fig: plt.Figure, filename: str) -> None:
    """Сохранение графика в reports/figures/ и screenshots/ в разрешении 300 DPI."""
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    path_fig = FIGURES_DIR / filename
    path_scr = SCREENSHOTS_DIR / filename

    fig.savefig(path_fig, dpi=300, bbox_inches="tight", facecolor=PALETTE["white"], pad_inches=0.2)
    shutil.copy2(path_fig, path_scr)
    plt.close(fig)
    logger.info("График сохранён: %s", filename)
