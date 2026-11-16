"""Модуль обратной совместимости для предобработки данных."""

from src.data.cleaner import clean_car_brand, clean_car_dataframe
from src.data.transformer import CarDataPreprocessor

__all__ = [
    "clean_car_brand",
    "clean_car_dataframe",
    "CarDataPreprocessor",
]
