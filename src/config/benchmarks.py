"""Метрики Loginom Studio и сопоставление файлов моделей."""

from typing import Dict, Any, List

LOGINOM_BENCHMARKS: Dict[str, Dict[str, Any]] = {
    "random_forest": {"r2": 0.9480, "rmse": 1820.6, "mae": 1350.0, "mape": 9.8},
    "linear_regression": {"r2": 0.8812, "rmse": 2845.3, "mae": 2050.0, "mape": 18.2},
    "neural_network": {"r2": 0.8540, "rmse": 3120.5, "mae": 2350.0, "mape": 20.4},
    "knn": {"r2": 0.8250, "rmse": 3410.2, "mae": 2400.0, "mape": 15.5},
}

MODEL_NAMES: List[str] = [
    "Случайный лес (Random Forest)",
    "Гребневая регрессия (Ridge)",
    "Нейронная сеть (MLP)",
    "Метод k-ближайших соседей (KNN)",
]

MODEL_FILE_MAP: Dict[str, str] = {
    "random_forest": "model_random_forest.joblib",
    "linear_regression": "model_linear_regression.joblib",
    "neural_network": "model_neural_network.joblib",
    "knn": "model_knn.joblib",
}

PREPROCESSOR_FILE = "preprocessor.joblib"

MODEL_KEY_MAP: Dict[str, str] = {
    "Случайный лес (Random Forest)": "random_forest",
    "Гребневая регрессия (Ridge)": "linear_regression",
    "Нейронная сеть (MLP)": "neural_network",
    "Метод k-ближайших соседей (KNN)": "knn",
    "random_forest": "random_forest",
    "linear_regression": "linear_regression",
    "neural_network": "neural_network",
    "knn": "knn",
}
