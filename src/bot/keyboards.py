"""Клавиатуры для Telegram-бота."""

from typing import Any, Dict, List, Optional
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from src.config import (
    ALLOWED_BODIES,
    BODY_LABELS,
    CAR_PRESETS,
    MODEL_KEY_MAP,
    MODEL_NAMES,
    MODEL_REGISTRY_INFO,
)

BTN_PRESETS = "Пресеты авто"
BTN_PREDICT = "Рассчитать авто"
BTN_HISTORY = "История"
BTN_STATS = "Статистика"
BTN_HELP = "Справка"
BTN_CANCEL = "Отмена"

POPULAR_BRANDS: List[str] = [
    "toyota", "bmw", "audi", "porsche",
    "honda", "mazda", "nissan", "subaru",
    "volkswagen", "volvo", "mitsubishi", "jaguar",
]


def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_PRESETS), KeyboardButton(text=BTN_PREDICT)],
            [KeyboardButton(text=BTN_HISTORY), KeyboardButton(text=BTN_STATS)],
            [KeyboardButton(text=BTN_HELP)],
        ],
        resize_keyboard=True,
    )


def cancel_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_CANCEL)]],
        resize_keyboard=True,
    )


def presets_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=name, callback_data=f"preset:{idx}")]
        for idx, name in enumerate(CAR_PRESETS.keys())
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def brands_kb() -> InlineKeyboardMarkup:
    rows = []
    for i in range(0, len(POPULAR_BRANDS), 3):
        chunk = POPULAR_BRANDS[i : i + 3]
        rows.append([
            InlineKeyboardButton(text=b.capitalize(), callback_data=f"brand:{b}")
            for b in chunk
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def bodies_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=BODY_LABELS.get(b, b.capitalize()), callback_data=f"body:{b}")]
        for b in ALLOWED_BODIES
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def models_kb(metrics: Optional[Dict[str, Any]] = None) -> InlineKeyboardMarkup:
    """Клавиатура выбора модели с версией и метрикой R² в скобках."""
    rows = []
    for idx, name in enumerate(MODEL_NAMES):
        key = MODEL_KEY_MAP.get(name, "random_forest")
        info = MODEL_REGISTRY_INFO.get(key, {})
        r2 = float(info.get("default_r2", 0.0))
        if metrics and key in metrics:
            test_m = metrics[key].get("test", metrics[key]) if isinstance(metrics[key], dict) else {}
            r2 = float(test_m.get("r2", r2))
        short_label = info.get("short_ru", name)
        version = info.get("version", "v2.2")
        btn_text = f"{short_label} {version} (R²={r2:.2f})"
        rows.append([InlineKeyboardButton(text=btn_text, callback_data=f"model:{idx}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
