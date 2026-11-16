"""Управление подключением и инициализация SQLite базы данных."""

import sqlite3
from pathlib import Path
from typing import Optional
from src.config import DB_FILE


def get_connection(db_path: Optional[Path | str] = None) -> sqlite3.Connection:
    """Получение подключения к SQLite с построчным доступом через Row."""
    target_path = Path(db_path) if db_path else DB_FILE
    target_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[Path | str] = None) -> None:
    """Создание таблиц, колонок и индексов базы данных."""
    with get_connection(db_path) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                username TEXT,
                timestamp TEXT NOT NULL,
                model_name TEXT NOT NULL,
                predicted_price_usd REAL NOT NULL,
                predicted_price_rub REAL NOT NULL,
                brand TEXT NOT NULL,
                carbody TEXT NOT NULL,
                horsepower REAL NOT NULL,
                enginesize REAL NOT NULL,
                curbweight REAL NOT NULL,
                citympg REAL,
                highwaympg REAL,
                raw_features_json TEXT,
                features_json TEXT
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_pred_user ON predictions(user_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_pred_time ON predictions(timestamp)")
        conn.commit()
