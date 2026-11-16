"""Трансформер предобработки признаков для обучения моделей."""

from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import joblib
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.config import (
    CATEGORICAL_FEATURES,
    NUMERICAL_FEATURES,
    FEATURE_DEFAULTS,
    MODELS_DIR,
    PREPROCESSOR_FILE,
)
from src.data.cleaner import clean_car_dataframe


class CarDataPreprocessor(BaseEstimator, TransformerMixin):
    """Сквозной пайплайн предобработки Scikit-Learn (OneHotEncoder + StandardScaler)."""

    def __init__(
        self,
        categorical_features: Optional[List[str]] = None,
        numerical_features: Optional[List[str]] = None,
    ) -> None:
        self.categorical_features = categorical_features or CATEGORICAL_FEATURES
        self.numerical_features = numerical_features or NUMERICAL_FEATURES
        self.transformer: ColumnTransformer = self._build_transformer()
        self.is_fitted = False

    def _build_transformer(self) -> ColumnTransformer:
        cat_pipe = Pipeline([
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ])
        num_pipe = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ])
        return ColumnTransformer(
            transformers=[
                ("num", num_pipe, self.numerical_features),
                ("cat", cat_pipe, self.categorical_features),
            ],
            remainder="drop",
        )

    def _prepare_df(self, X: pd.DataFrame) -> pd.DataFrame:
        if "brand" not in X.columns or "power_to_weight" not in X.columns:
            return clean_car_dataframe(X)
        return X

    def fit(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> "CarDataPreprocessor":
        df = self._prepare_df(X)
        self.transformer.fit(df, y)
        self.is_fitted = True
        return self

    def transform(self, X: pd.DataFrame) -> np.ndarray:
        df = self._prepare_df(X)
        return self.transformer.transform(df)

    def fit_transform(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> np.ndarray:
        return self.fit(X, y).transform(X)

    def transform_dict(self, input_dict: Dict[str, Any]) -> np.ndarray:
        merged = FEATURE_DEFAULTS.copy()
        merged.update(input_dict)
        if "horsepower" in merged and "curbweight" in merged and merged["curbweight"] > 0:
            merged["power_to_weight"] = merged["horsepower"] / merged["curbweight"]
        if "enginesize" in merged and "curbweight" in merged and merged["curbweight"] > 0:
            merged["engine_to_weight"] = merged["enginesize"] / merged["curbweight"]
        df_single = pd.DataFrame([merged])
        return self.transformer.transform(df_single)

    def save(self, filepath: Optional[Union[Path, str]] = None) -> Path:
        out_path = Path(filepath) if filepath else MODELS_DIR / PREPROCESSOR_FILE
        out_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, out_path)
        return out_path

    @classmethod
    def load(cls, filepath: Optional[Union[Path, str]] = None) -> "CarDataPreprocessor":
        in_path = Path(filepath) if filepath else MODELS_DIR / PREPROCESSOR_FILE
        return joblib.load(in_path)
