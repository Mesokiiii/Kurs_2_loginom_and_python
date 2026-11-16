"""Unit tests for typo correction, feature engineering, and data preprocessing.
"""

import pandas as pd
import numpy as np
import pytest

from src.data.preprocessor import (
    clean_car_brand,
    clean_car_dataframe,
    CarDataPreprocessor,
)
from src.data.data_loader import validate_dataset, load_raw_data
from src.config import RAW_DATA_PATH


def test_clean_car_brand_typos():
    """Verifies that all known brand typographical errors are accurately corrected."""
    test_cases = {
        "vokswagen rabbit": "volkswagen",
        "vw golf": "volkswagen",
        "volkswagen jetta": "volkswagen",
        "maxda rx7": "mazda",
        "mazda 6": "mazda",
        "porcshce 911": "porsche",
        "porsche cayenne": "porsche",
        "toyouta corolla": "toyota",
        "toyota camry": "toyota",
        "alfa-romero giulia": "alfa-romeo",
        "BMW 320i": "bmw",
        "  audi 100ls  ": "audi",
        "": "toyota",
    }

    for input_name, expected_brand in test_cases.items():
        assert clean_car_brand(input_name) == expected_brand, f"Failed for {input_name}"


def test_clean_car_dataframe_transformations():
    """Verifies dataframe cleaning, word-to-num conversions, and engineered features."""
    sample_data = pd.DataFrame({
        "car_ID": [1, 2],
        "CarName": ["toyouta corolla", "maxda rx-4"],
        "doornumber": ["two", "four"],
        "cylindernumber": ["four", "six"],
        "horsepower": [100.0, 150.0],
        "enginesize": [120.0, 180.0],
        "curbweight": [2000.0, 3000.0],
        "fueltype": ["gas", "gas"],
        "aspiration": ["std", "turbo"],
        "carbody": ["sedan", "hatchback"],
    })

    cleaned = clean_car_dataframe(sample_data)

    # Проверка удаления технического car_ID
    assert "car_ID" not in cleaned.columns
    # Проверка выделения марки автомобиля
    assert "CarName" not in cleaned.columns
    assert "brand" in cleaned.columns
    assert list(cleaned["brand"]) == ["toyota", "mazda"]

    # Проверка преобразования текстовых числительных
    assert list(cleaned["doornumber"]) == [2, 4]
    assert list(cleaned["cylindernumber"]) == [4, 6]

    # Проверка создания производных признаков
    assert "power_to_weight" in cleaned.columns
    assert "engine_to_weight" in cleaned.columns
    assert np.isclose(cleaned["power_to_weight"].iloc[0], 100.0 / 2000.0)
    assert np.isclose(cleaned["engine_to_weight"].iloc[0], 120.0 / 2000.0)


def test_cardata_preprocessor_fit_transform():
    """Verifies that CarDataPreprocessor properly transforms data into a 2D numeric matrix."""
    raw_df = load_raw_data(RAW_DATA_PATH)
    preprocessor = CarDataPreprocessor()

    features_matrix = preprocessor.fit_transform(raw_df)

    assert isinstance(features_matrix, np.ndarray)
    assert features_matrix.ndim == 2
    assert features_matrix.shape[0] == len(raw_df)
    assert features_matrix.shape[1] > 20
    assert not np.isnan(features_matrix).any()


def test_cardata_preprocessor_transform_dict():
    """Verifies single dictionary transformation with defaults."""
    preprocessor = CarDataPreprocessor.load()

    single_input = {
        "brand": "bmw",
        "carbody": "sedan",
        "horsepower": 180.0,
        "enginesize": 160.0,
        "curbweight": 3000.0,
    }

    x_proc = preprocessor.transform_dict(single_input)
    assert isinstance(x_proc, np.ndarray)
    assert x_proc.shape[0] == 1
    assert not np.isnan(x_proc).any()


def test_validate_dataset_schema():
    """Tests the dataset validation logic for presence of required columns."""
    valid_df = pd.DataFrame({
        "CarName": ["toyota corolla"],
        "fueltype": ["gas"],
        "aspiration": ["std"],
        "carbody": ["sedan"],
        "horsepower": [100.0],
        "enginesize": [120.0],
        "curbweight": [2500.0],
        "price": [12000.0],
    })

    res = validate_dataset(valid_df)
    assert res.is_valid is True
    assert res.target_present is True
    assert len(res.errors) == 0

    # Проверка обработки отсутствия целевой переменной
    invalid_df = valid_df.drop(columns=["price"])
    res_inv = validate_dataset(invalid_df)
    assert res_inv.is_valid is False
    assert res_inv.target_present is False
