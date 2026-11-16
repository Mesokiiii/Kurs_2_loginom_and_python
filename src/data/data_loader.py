"""Модуль обратной совместимости для загрузки данных."""

from src.data.loader import load_raw_data, load_processed_data
from src.data.validator import validate_dataset, DatasetValidationResult

__all__ = [
    "load_raw_data",
    "load_processed_data",
    "validate_dataset",
    "DatasetValidationResult",
]
