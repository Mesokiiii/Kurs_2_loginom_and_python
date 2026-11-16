"""Главный скрипт для подготовки данных, построения графиков и обучения моделей.

Запуск:
    python train_models.py
"""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import logging
from pathlib import Path

# Корень проекта
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data.data_loader import load_raw_data
from src.data.preprocessor import clean_car_dataframe
from src.analytics.visualizations import generate_all_eda_visualizations
from src.models.train import train_and_evaluate_all

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Полный цикл обработки: загрузка, предобработка, графики и обучение моделей."""
    logger.info("Запуск обучения моделей прогнозирования цен на автомобили")

    # Загрузка и предобработка данных
    logger.info("Загрузка исходного набора данных...")
    df_raw = load_raw_data()
    logger.info("Данные успешно загружены, размерность: %s", df_raw.shape)

    logger.info("Очистка названий марок и формирование признаков...")
    df_clean = clean_car_dataframe(df_raw)
    logger.info("Предобработка завершена, количество признаков: %d", df_clean.shape[1])

    # Построение графиков EDA и срезов OLAP
    logger.info("Построение аналитических графиков...")
    generate_all_eda_visualizations(df_clean)

    # Обучение и оценка качества моделей
    logger.info("Обучение 4 алгоритмов регрессии (Random Forest, Ridge, MLP, KNN)...")
    trained_models, preprocessor, metrics_summary = train_and_evaluate_all()

    logger.info("Обучение моделей успешно завершено")
    print("\n" + "-" * 75)
    print("Результаты оценки моделей на тестовой выборке:")
    print("-" * 75)
    for model_name, metrics in metrics_summary.items():
        if isinstance(metrics, dict) and "test" in metrics:
            test_m = metrics["test"]
            r2 = test_m.get("r2", 0)
            rmse = test_m.get("rmse", 0)
            mae = test_m.get("mae", 0)
            mape = test_m.get("mape", 0)
            print(f"* {model_name:20s} | R^2 = {r2:.4f} | RMSE = ${rmse:,.2f} | MAE = ${mae:,.2f} | MAPE = {mape:.2f}%")
    print("-" * 75 + "\n")


if __name__ == "__main__":
    main()
