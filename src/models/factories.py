"""Инициализация и конфигурация алгоритмов регрессии."""

from typing import Dict, Any
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.neural_network import MLPRegressor
from sklearn.neighbors import KNeighborsRegressor

from src.config import RANDOM_STATE


def create_regressors() -> Dict[str, Any]:
    """Создание 4 исследуемых моделей с подобранными гиперпараметрами."""
    return {
        "random_forest": RandomForestRegressor(
            n_estimators=120,
            max_depth=12,
            min_samples_split=3,
            random_state=RANDOM_STATE,
            n_jobs=-1,
        ),
        "linear_regression": Ridge(
            alpha=1.5,
            random_state=RANDOM_STATE,
        ),
        "neural_network": MLPRegressor(
            hidden_layer_sizes=(64, 32),
            activation="relu",
            max_iter=500,
            early_stopping=True,
            random_state=RANDOM_STATE,
        ),
        "knn": KNeighborsRegressor(
            n_neighbors=5,
            weights="distance",
        ),
    }
