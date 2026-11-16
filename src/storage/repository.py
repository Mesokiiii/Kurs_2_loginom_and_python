"""Репозиторий операций сохранения и выборки расчетов цен."""

import json
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from src.storage.connection import get_connection, init_db


def log_prediction(
    user_id: str | int,
    predicted_price_usd: float,
    predicted_price_rub: float,
    model_name: str,
    features: Dict[str, Any],
    username: Optional[str] = None,
    db_path: Optional[Path | str] = None,
) -> int:
    """Сохранение результата прогноза в базу данных."""
    init_db(db_path)
    brand = str(features.get("brand", "toyota")).lower()
    carbody = str(features.get("carbody", "sedan")).lower()
    hp = float(features.get("horsepower", 100.0))
    eng = float(features.get("enginesize", 120.0))
    weight = float(features.get("curbweight", 2400.0))
    city_mpg = float(features.get("citympg", 25.0))
    hwy_mpg = float(features.get("highwaympg", 30.0))
    payload = json.dumps(features, ensure_ascii=False)
    now_ts = datetime.datetime.now().isoformat()

    with get_connection(db_path) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO predictions (
                user_id, username, timestamp, model_name,
                predicted_price_usd, predicted_price_rub,
                brand, carbody, horsepower, enginesize, curbweight,
                citympg, highwaympg, raw_features_json, features_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (str(user_id), username, now_ts, model_name,
             predicted_price_usd, predicted_price_rub,
             brand, carbody, hp, eng, weight,
             city_mpg, hwy_mpg, payload, payload),
        )
        conn.commit()
        return cur.lastrowid or 0


def get_user_history(user_id: str | int, limit: int = 5, db_path: Optional[Path | str] = None) -> List[Dict[str, Any]]:
    """Выборка последних прогнозов конкретного пользователя."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM predictions WHERE user_id = ? ORDER BY id DESC LIMIT ?", (str(user_id), limit))
        return [dict(r) for r in cur.fetchall()]


def get_recent_predictions(limit: int = 10, db_path: Optional[Path | str] = None) -> List[Dict[str, Any]]:
    """Выборка последних расчетов среди всех пользователей."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM predictions ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(r) for r in cur.fetchall()]


def get_overall_stats(db_path: Optional[Path | str] = None) -> Dict[str, Any]:
    """Сбор общей статистики по выполненным расчетам."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*), COUNT(DISTINCT user_id), AVG(predicted_price_usd), MIN(predicted_price_usd), MAX(predicted_price_usd) FROM predictions")
        row = cur.fetchone() or (0, 0, 0.0, 0.0, 0.0)
        total, users = int(row[0] or 0), int(row[1] or 0)
        avg_p, min_p, max_p = float(row[2] or 0.0), float(row[3] or 0.0), float(row[4] or 0.0)

        top_brand, top_model = "toyota", "Случайный лес"
        if total > 0:
            cur.execute("SELECT brand FROM predictions GROUP BY brand ORDER BY COUNT(*) DESC LIMIT 1")
            b_row = cur.fetchone()
            top_brand = b_row[0] if b_row else top_brand
            cur.execute("SELECT model_name FROM predictions GROUP BY model_name ORDER BY COUNT(*) DESC LIMIT 1")
            m_row = cur.fetchone()
            top_model = m_row[0] if m_row else top_model

        return {
            "total_queries": total,
            "unique_users": users,
            "avg_predicted_price_usd": round(avg_p, 2),
            "min_predicted_price_usd": round(min_p, 2),
            "max_predicted_price_usd": round(max_p, 2),
            "top_brand": top_brand,
            "top_model": top_model,
        }
