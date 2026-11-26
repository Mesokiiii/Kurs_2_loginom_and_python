"""Валидация схемы датасета и ограничитель входных параметров автомобиля."""

from typing import Dict, Any, List, Tuple
from dataclasses import dataclass, field
import pandas as pd

from src.config import (
    TARGET_COL,
    FEATURE_DEFAULTS,
    FEATURE_RANGES,
    ALLOWED_BRANDS,
    ALLOWED_BODIES,
    ALLOWED_FUELS,
    ALLOWED_ASPIRATIONS,
    ALLOWED_DRIVES,
)

NUMERIC_FEATURE_META: Dict[str, Tuple[str, str]] = {
    "horsepower": ("Мощность двигателя", "л.с."),
    "enginesize": ("Объём двигателя", "куб. дюймов"),
    "curbweight": ("Снаряжённая масса", "фунтов"),
    "citympg": ("Расход топлива (город)", "миль/галлон"),
    "highwaympg": ("Расход топлива (трасса)", "миль/галлон"),
    "wheelbase": ("Колёсная база", "дюймов"),
    "carlength": ("Длина кузова", "дюймов"),
    "carwidth": ("Ширина кузова", "дюймов"),
}

CATEGORICAL_ALLOWED_MAP: Dict[str, Tuple[List[str], str]] = {
    "brand": (ALLOWED_BRANDS, "Марка автомобиля"),
    "carbody": (ALLOWED_BODIES, "Тип кузова"),
    "fueltype": (ALLOWED_FUELS, "Тип топлива"),
    "aspiration": (ALLOWED_ASPIRATIONS, "Тип наддува"),
    "drivewheel": (ALLOWED_DRIVES, "Тип привода"),
}


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


def clamp_car_features(features: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """Ограничивает числовые и категориальные параметры автомобиля допустимыми пределами.

    Возвращает кортеж (очищенный словарь признаков, список предупреждений на русском языке).
    """
    clamped: Dict[str, Any] = dict(features)
    warnings: List[str] = []

    for key, (min_val, max_val, _step) in FEATURE_RANGES.items():
        if key not in clamped or clamped[key] is None:
            continue
        label, unit = NUMERIC_FEATURE_META.get(key, (key, ""))
        unit_suffix = f" {unit}" if unit else ""
        try:
            val = float(clamped[key])
        except (TypeError, ValueError):
            default_val = float(FEATURE_DEFAULTS.get(key, min_val))
            clamped[key] = default_val
            warnings.append(
                f"{label}: некорректное значение — заменено на значение по умолчанию {default_val:g}{unit_suffix} "
                f"(допустимый диапазон: {min_val:g}–{max_val:g}{unit_suffix})."
            )
            continue

        if val < min_val:
            clamped[key] = float(min_val)
            warnings.append(
                f"{label}: значение {val:g}{unit_suffix} ниже минимума — "
                f"ограничено до {min_val:g}{unit_suffix} (допустимо {min_val:g}–{max_val:g}{unit_suffix})."
            )
        elif val > max_val:
            clamped[key] = float(max_val)
            warnings.append(
                f"{label}: значение {val:g}{unit_suffix} выше максимума — "
                f"ограничено до {max_val:g}{unit_suffix} (допустимо {min_val:g}–{max_val:g}{unit_suffix})."
            )
        else:
            clamped[key] = val

    for cat_key, (allowed, label) in CATEGORICAL_ALLOWED_MAP.items():
        if cat_key not in clamped or clamped[cat_key] is None:
            continue
        raw_str = str(clamped[cat_key]).strip().lower()
        if raw_str not in allowed:
            default_cat = str(FEATURE_DEFAULTS.get(cat_key, allowed[0]))
            clamped[cat_key] = default_cat
            warnings.append(
                f"{label}: недопустимое значение «{features[cat_key]}» — "
                f"заменено на «{default_cat}»."
            )
        else:
            clamped[cat_key] = raw_str

    return clamped, warnings
