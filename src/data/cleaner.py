"""Очистка текстовых данных и нормализация марок автомобилей."""

from typing import Dict, Any
import pandas as pd

from src.config import BRAND_CORRECTIONS, WORD_NUM_MAP


def clean_car_brand(raw_name: str) -> str:
    """Извлечение названия марки из строки и исправление опечаток."""
    if not isinstance(raw_name, str) or not raw_name.strip():
        return "toyota"

    tokens = raw_name.strip().split()
    brand_raw = tokens[0].lower() if tokens else "toyota"
    return BRAND_CORRECTIONS.get(brand_raw, brand_raw)


def clean_car_dataframe(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Очистка датасета, исправление опечаток и генерация производных признаков."""
    df = df_raw.copy()

    if "car_ID" in df.columns:
        df = df.drop(columns=["car_ID"])

    if "CarName" in df.columns:
        df["brand"] = df["CarName"].apply(clean_car_brand)
        df = df.drop(columns=["CarName"])

    for col in ["doornumber", "cylindernumber"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.lower().map(WORD_NUM_MAP).fillna(4).astype(int)

    # Вычисляемые признаки
    if "horsepower" in df.columns and "curbweight" in df.columns:
        df["power_to_weight"] = df["horsepower"] / df["curbweight"]

    if "enginesize" in df.columns and "curbweight" in df.columns:
        df["engine_to_weight"] = df["enginesize"] / df["curbweight"]

    # Приведение типов
    num_candidates = [
        "wheelbase", "carlength", "carwidth", "carheight", "curbweight",
        "enginesize", "boreratio", "stroke", "compressionratio", "horsepower",
        "peakrpm", "citympg", "highwaympg", "price",
    ]
    for col in num_candidates:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    cat_candidates = [
        "brand", "fueltype", "aspiration", "carbody",
        "drivewheel", "enginelocation", "enginetype", "fuelsystem",
    ]
    for col in cat_candidates:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.lower()

    return df
