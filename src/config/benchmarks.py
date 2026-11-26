"""Метрики Loginom Studio, реестр версий моделей и сопоставление файлов моделей."""

from typing import Dict, Any, List, Optional

from src.config.meta import MODEL_VERSION

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

MODEL_REGISTRY_INFO: Dict[str, Dict[str, Any]] = {
    "random_forest": {
        "version": MODEL_VERSION,
        "short_ru": "Случайный лес",
        "algorithm_ru": "Случайный лес (RandomForestRegressor, ансамбль решающих деревьев)",
        "trained_on": "164 авто (80% выборки, StandardScaler + OneHotEncoder)",
        "hyperparams": "n_estimators=120, max_depth=12, min_samples_split=3, random_state=42",
        "error_criterion": "MSE (среднеквадратичная ошибка) + контроль R², MAE, RMSE, MAPE",
        "default_r2": 0.9582,
        "default_mape": 9.14,
    },
    "linear_regression": {
        "version": MODEL_VERSION,
        "short_ru": "Гребневая регрессия Ridge",
        "algorithm_ru": "Гребневая линейная регрессия (Ridge, L2-регуляризация)",
        "trained_on": "164 авто (80% выборки, StandardScaler + OneHotEncoder)",
        "hyperparams": "alpha=1.5, random_state=42",
        "error_criterion": "MSE с L2-штрафом + контроль R², MAE, RMSE, MAPE",
        "default_r2": 0.8986,
        "default_mape": 16.90,
    },
    "neural_network": {
        "version": MODEL_VERSION,
        "short_ru": "Нейронная сеть MLP",
        "algorithm_ru": "Многослойный перцептрон (MLPRegressor, нейросеть)",
        "trained_on": "164 авто (80% выборки, StandardScaler + OneHotEncoder)",
        "hyperparams": "hidden_layer_sizes=(64, 32), activation='relu', max_iter=500, early_stopping=True",
        "error_criterion": "MSE с ранней остановкой + контроль R², MAE, RMSE, MAPE",
        "default_r2": 0.8537,
        "default_mape": 18.68,
    },
    "knn": {
        "version": MODEL_VERSION,
        "short_ru": "Метод k-ближайших соседей KNN",
        "algorithm_ru": "Метод k-ближайших соседей (KNeighborsRegressor, взвешенный по расстоянию)",
        "trained_on": "164 авто (80% выборки, StandardScaler + OneHotEncoder)",
        "hyperparams": "n_neighbors=5, weights='distance'",
        "error_criterion": "Евклидова метрика + контроль R², MAE, RMSE, MAPE",
        "default_r2": 0.7702,
        "default_mape": 15.08,
    },
}


def format_model_with_quality(
    model_name_or_key: str,
    metrics: Optional[Dict[str, Any]] = None,
) -> str:
    """Возвращает название модели с версией и показателями качества в скобках."""
    key = MODEL_KEY_MAP.get(model_name_or_key, model_name_or_key)
    info = MODEL_REGISTRY_INFO.get(key)
    if not info:
        return f"{model_name_or_key} {MODEL_VERSION}"

    r2 = float(info["default_r2"])
    mape = float(info["default_mape"])
    if metrics and key in metrics:
        model_m = metrics[key]
        test_m = model_m.get("test", model_m) if isinstance(model_m, dict) else {}
        if "r2" in test_m:
            r2 = float(test_m["r2"])
        if "mape" in test_m:
            mape = float(test_m["mape"])

    return f"{info['short_ru']} {info['version']} (R² = {r2:.2f}, ошибка {mape:.1f}%)"
