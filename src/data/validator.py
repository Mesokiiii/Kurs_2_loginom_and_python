"""Валидация схемы и целостности датасета."""

from typing import Dict, Any, List
from dataclasses import dataclass, field
import pandas as pd

from src.config import TARGET_COL


@dataclass
class DatasetValidationResult:
    """Результаты проверки корректности набора данных."""
    is_valid: bool
    total_rows: int
    total_columns: int
    missing_columns: List[str] = field(default_factory=list)
    target_present: bool = True
    null_counts: Dict[str, int] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


def validate_dataset(df: pd.DataFrame, require_target: bool = True) -> DatasetValidationResult:
    """Проверка структуры, обязательных колонок и пропусков в датасете."""
    errors: List[str] = []
    missing_cols: List[str] = []

    essential_cols = [
        "CarName", "fueltype", "aspiration", "carbody",
        "horsepower", "enginesize", "curbweight",
    ]

    for col in essential_cols:
        if col not in df.columns:
            missing_cols.append(col)
            errors.append(f"Отсутствует обязательная колонка: {col}")

    target_present = TARGET_COL in df.columns
    if require_target and not target_present:
        errors.append(f"Отсутствует целевая переменная: {TARGET_COL}")

    null_counts = {col: int(df[col].isna().sum()) for col in df.columns if df[col].isna().sum() > 0}
    is_valid = len(errors) == 0

    return DatasetValidationResult(
        is_valid=is_valid,
        total_rows=len(df),
        total_columns=len(df.columns),
        missing_columns=missing_cols,
        target_present=target_present,
        null_counts=null_counts,
        errors=errors,
    )
