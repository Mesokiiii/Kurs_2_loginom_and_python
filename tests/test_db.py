"""Unit tests for SQLite database storage and prediction history logging.
"""

import pytest
from src.storage import (
    init_db,
    log_prediction,
    get_user_history,
    get_recent_predictions,
    get_overall_stats,
)


@pytest.fixture
def temp_db(tmp_path):
    """Provides a fresh isolated SQLite database file for testing."""
    db_file = tmp_path / "test_predictions.db"
    init_db(db_file)
    return db_file


def test_db_initialization(temp_db):
    """Verifies that empty database initializes properly."""
    assert temp_db.exists()
    stats = get_overall_stats(db_path=temp_db)
    assert stats["total_queries"] == 0
    assert stats["unique_users"] == 0


def test_log_prediction_and_history(temp_db):
    """Tests logging a prediction and querying user history."""
    features_1 = {
        "brand": "toyota",
        "carbody": "hatchback",
        "horsepower": 75.0,
        "enginesize": 95.0,
        "curbweight": 2100.0,
    }
    rec_id_1 = log_prediction(
        user_id="user_101",
        predicted_price_usd=7200.0,
        predicted_price_rub=673200.0,
        model_name="Random Forest",
        features=features_1,
        username="TestUser1",
        db_path=temp_db,
    )
    assert rec_id_1 == 1

    features_2 = {
        "brand": "bmw",
        "carbody": "sedan",
        "horsepower": 185.0,
        "enginesize": 165.0,
        "curbweight": 3200.0,
    }
    rec_id_2 = log_prediction(
        user_id="user_101",
        predicted_price_usd=21500.0,
        predicted_price_rub=2010250.0,
        model_name="Ridge",
        features=features_2,
        username="TestUser1",
        db_path=temp_db,
    )
    assert rec_id_2 == 2

    # Проверка выборки истории пользователя
    history = get_user_history(user_id="user_101", limit=10, db_path=temp_db)
    assert len(history) == 2
    # Проверка сортировки по убыванию ID
    assert history[0]["id"] == 2
    assert history[0]["brand"] == "bmw"
    assert history[1]["id"] == 1
    assert history[1]["brand"] == "toyota"


def test_db_overall_stats(temp_db):
    """Verifies aggregate statistics computation."""
    # Вставка тестовых записей для проверки статистики
    log_prediction("u1", 10000.0, 935000.0, "RF", {"brand": "toyota"}, db_path=temp_db)
    log_prediction("u1", 20000.0, 1870000.0, "RF", {"brand": "toyota"}, db_path=temp_db)
    log_prediction("u2", 30000.0, 2805000.0, "MLP", {"brand": "porsche"}, db_path=temp_db)

    stats = get_overall_stats(db_path=temp_db)
    assert stats["total_queries"] == 3
    assert stats["unique_users"] == 2
    assert stats["avg_predicted_price_usd"] == 20000.0
    assert stats["min_predicted_price_usd"] == 10000.0
    assert stats["max_predicted_price_usd"] == 30000.0
    assert stats["top_brand"] == "toyota"
    assert stats["top_model"] == "RF"
