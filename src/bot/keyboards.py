"""Клавиатуры для Telegram-бота."""

from typing import List
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from src.config import ALLOWED_BODIES, CAR_PRESETS, MODEL_NAMES

BTN_PRESETS = "Пресеты авто"
BTN_PREDICT = "Рассчитать авто"
BTN_HISTORY = "История"
BTN_STATS = "Статистика"
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
        [InlineKeyboardButton(text=b.capitalize(), callback_data=f"body:{b}")]
        for b in ALLOWED_BODIES
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def models_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=name, callback_data=f"model:{idx}")]
        for idx, name in enumerate(MODEL_NAMES)
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)
