"""Обучение, валидация и сериализация моделей регрессии."""

from pathlib import Path
from typing import Dict, Any, Tuple, Optional
import json
import logging
import joblib
import numpy as np
from sklearn.model_selection import train_test_split

from src.config import (
    MODELS_DIR,
    METRICS_PATH,
    METADATA_PATH,
    TARGET_COL,
    RANDOM_STATE,
    TEST_SIZE,
    MODEL_VERSION,
    TRAIN_SPLIT_LABEL,
    MODEL_FILE_MAP,
    PREPROCESSOR_FILE,
    LOGINOM_BENCHMARKS,
)
from src.data.loader import load_raw_data
from src.data.cleaner import clean_car_dataframe
from src.data.transformer import CarDataPreprocessor
from src.models.metrics import compute_metrics
from src.models.factories import create_regressors

logger = logging.getLogger(__name__)


def train_and_evaluate_all(
    data_path: Optional[Path | str] = None,
) -> Tuple[Dict[str, Any], CarDataPreprocessor, Dict[str, Any]]:
    """Полный цикл обучения 4 моделей, оценка метрик и сохранение артефактов."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)

    df_raw = load_raw_data(data_path)
    df_clean = clean_car_dataframe(df_raw)

    y = df_clean[TARGET_COL].values
    X_df = df_clean.drop(columns=[TARGET_COL])

    X_train_raw, X_test_raw, y_train, y_test = train_test_split(
        X_df, y, test_size=TEST_SIZE, random_state=RANDOM_STATE
    )

    preprocessor = CarDataPreprocessor()
    X_train = preprocessor.fit_transform(X_train_raw)
    X_test = preprocessor.transform(X_test_raw)

    regressors = create_regressors()
    trained_models: Dict[str, Any] = {}
    metrics_summary: Dict[str, Any] = {}
    residual_stds: Dict[str, float] = {}

    for name, model in regressors.items():
        model.fit(X_train, y_train)
        trained_models[name] = model

        train_pred = model.predict(X_train)
        test_pred = model.predict(X_test)
        residuals = y_test - test_pred
        std_err = round(float(np.std(residuals)), 2)
        residual_stds[name] = std_err

        metrics_summary[name] = {
            "version": MODEL_VERSION,
            "train": compute_metrics(y_train, train_pred),
            "test": compute_metrics(y_test, test_pred),
            "residual_std": std_err,
            "loginom_benchmark": LOGINOM_BENCHMARKS.get(name, {}),
        }

        # Сохранение весов
        joblib.dump(model, MODELS_DIR / MODEL_FILE_MAP[name])

    # Сохранение лучшей модели и препроцессора
    if "random_forest" in trained_models:
        joblib.dump(trained_models["random_forest"], MODELS_DIR / "best_model_pipeline.joblib")
    preprocessor.save(MODELS_DIR / PREPROCESSOR_FILE)

    with open(METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(metrics_summary, f, indent=2, ensure_ascii=False)

    metadata = {
        "model_version": MODEL_VERSION,
        "train_split_label": TRAIN_SPLIT_LABEL,
        "trained_models": list(trained_models.keys()),
        "model_versions": {k: MODEL_VERSION for k in trained_models.keys()},
        "dataset_rows": len(df_raw),
        "train_samples": int(len(X_train_raw)),
        "test_samples": int(len(X_test_raw)),
        "features_count": int(X_train.shape[1]),
        "random_state": RANDOM_STATE,
        "test_size": TEST_SIZE,
        "target_mean": float(np.mean(y)),
        "target_std": float(np.std(y)),
        "target_median": float(np.median(y)),
        "target_min": float(np.min(y)),
        "target_max": float(np.max(y)),
        "residual_stds": residual_stds,
    }
    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    return trained_models, preprocessor, metrics_summary
