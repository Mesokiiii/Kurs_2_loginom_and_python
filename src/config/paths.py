"""Пути к каталогам и ключевым файлам проекта."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
REPORTS_DIR = BASE_DIR / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
SCREENSHOTS_DIR = BASE_DIR / "screenshots"
STORAGE_DIR = BASE_DIR / "src" / "storage"

RAW_DATA_PATH = DATA_DIR / "CarPrice_Assignment.csv"
PROCESSED_DATA_PATH = DATA_DIR / "processed_car_data.csv"
METRICS_PATH = REPORTS_DIR / "metrics.json"
METADATA_PATH = MODELS_DIR / "metadata.json"
DB_FILE = STORAGE_DIR / "predictions.db"
