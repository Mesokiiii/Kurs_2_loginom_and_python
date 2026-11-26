"""Раздел истории расчётов в локальной базе SQLite и сравнения моделей."""

import pandas as pd
import streamlit as st

from src.config import (
    BODY_LABELS,
    LOGINOM_BENCHMARKS,
    MODEL_REGISTRY_INFO,
    MODEL_VERSION,
    TRAIN_SPLIT_LABEL,
    USD_TO_RUB_RATE,
    format_rub,
)
from src.models.service import ModelService
from src.storage.repository import get_overall_stats, get_recent_predictions


def render_history_page(service: ModelService) -> None:
    """Отрисовывает историю прогнозов из локальной базы SQLite и сводку качества моделей."""
    st.header("История расчётов (локальная база SQLite)")
    st.caption(
        "Локальная база SQLite используется для логирования расчётов из веб-интерфейса и Telegram-бота. "
        "Все денежные показатели отображаются в рублях (₽)."
    )

    stats = get_overall_stats()
    avg_rub = stats["avg_predicted_price_usd"] * USD_TO_RUB_RATE
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Всего расчётов", stats["total_queries"])
    c2.metric("Уникальных пользователей", stats["unique_users"])
    c3.metric("Средняя прогнозная цена", format_rub(avg_rub))
    c4.metric("Популярная марка", str(stats["top_brand"]).capitalize())

    st.subheader("Последние расчёты в локальной базе SQLite")
    recent = get_recent_predictions(limit=15)
    if recent:
        table = [
            {
                "ID": r["id"],
                "Время": str(r["timestamp"])[:19].replace("T", " "),
                "Источник": r["username"] or r["user_id"],
                "Марка": str(r["brand"]).capitalize(),
                "Кузов": BODY_LABELS.get(str(r["carbody"]).lower(), str(r["carbody"]).capitalize()),
                "Мощность (л.с.)": int(r["horsepower"]),
                "Прогноз (₽)": format_rub(
                    r.get("predicted_price_rub")
                    if r.get("predicted_price_rub")
                    else float(r.get("predicted_price_usd", 0)) * USD_TO_RUB_RATE
                ),
                "Модель": r["model_name"],
            }
            for r in recent
        ]
        st.dataframe(pd.DataFrame(table), use_container_width=True, hide_index=True)
    else:
        st.info("Локальная база SQLite для логирования расчётов пока пуста. Выполните первый прогноз.")

    st.subheader(f"Сравнение качества моделей ({MODEL_VERSION}): Python vs Loginom")
    st.caption(f"Схема разбиения данных: {TRAIN_SPLIT_LABEL}.")
    metrics = service.get_metrics_summary()

    rows = []
    for key, info in MODEL_REGISTRY_INFO.items():
        py_m = metrics.get(key, {})
        train_m = py_m.get("train", {}) if isinstance(py_m, dict) else {}
        test_m = py_m.get("test", py_m) if isinstance(py_m, dict) else {}
        lg_m = LOGINOM_BENCHMARKS.get(key, {})

        mae_k_rub = float(test_m.get("mae", 0.0)) * USD_TO_RUB_RATE / 1000.0
        rmse_k_rub = float(test_m.get("rmse", 0.0)) * USD_TO_RUB_RATE / 1000.0

        rows.append(
            {
                "Модель (версия)": f"{info['short_ru']} {info['version']}",
                "R² обучение": f"{float(train_m.get('r2', 0.0)):.4f}",
                "R² тест (Python)": f"{float(test_m.get('r2', info['default_r2'])):.4f}",
                "R² тест (Loginom)": f"{float(lg_m.get('r2', 0.0)):.4f}",
                "MAE (тыс. руб.)": f"{mae_k_rub:,.1f}".replace(",", " "),
                "RMSE (тыс. руб.)": f"{rmse_k_rub:,.1f}".replace(",", " "),
                "MAPE (%)": f"{float(test_m.get('mape', info['default_mape'])):.2f}%",
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
