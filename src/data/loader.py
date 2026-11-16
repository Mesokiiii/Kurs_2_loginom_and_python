"""Загрузка данных из CSV файлов."""

from pathlib import Path
from typing import Optional
import logging
import pandas as pd

from src.config import RAW_DATA_PATH, PROCESSED_DATA_PATH

logger = logging.getLogger(__name__)


def load_raw_data(path: Optional[Path | str] = None) -> pd.DataFrame:
    """Загрузка исходного датасета автомобилей из CSV."""
    target_path = Path(path) if path else RAW_DATA_PATH
    if not target_path.exists():
        raise FileNotFoundError(f"Файл датасета не найден: {target_path}")

    df = pd.read_csv(target_path)
    logger.info("Загружен датасет: %s, форма: %s", target_path.name, df.shape)
    return df


def load_processed_data(path: Optional[Path | str] = None) -> pd.DataFrame:
    """Загрузка предобработанного датасета из CSV."""
    target_path = Path(path) if path else PROCESSED_DATA_PATH
    if not target_path.exists():
        raise FileNotFoundError(f"Файл предобработанных данных не найден: {target_path}")

    df = pd.read_csv(target_path)
    logger.info("Загружены предобработанные данные: %s, форма: %s", target_path.name, df.shape)
    return df
