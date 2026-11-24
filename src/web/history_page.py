"""Раздел истории расчётов и сведений о проекте."""

import pandas as pd
import streamlit as st

from src.config import (
    STUDENT_NAME,
    STUDENT_GROUP,
    UNIVERSITY_NAME,
    COURSE_TOPIC,
    COURSE_VARIANT,
    LOGINOM_BENCHMARKS,
    MODEL_KEY_MAP,
)
from src.models.service import ModelService
from src.storage.repository import get_overall_stats, get_recent_predictions


def render_history_page(service: ModelService) -> None:
    """Отрисовывает историю прогнозов из SQLite и сравнение моделей."""
    st.header("История расчётов и о проекте")

    stats = get_overall_stats()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Всего расчётов", stats["total_queries"])
    c2.metric("Пользователей", stats["unique_users"])
    c3.metric("Средняя цена", f"${stats['avg_predicted_price_usd']:,.0f}")
    c4.metric("Популярная марка", str(stats["top_brand"]).capitalize())

    st.subheader("Последние расчёты (SQLite)")
    recent = get_recent_predictions(limit=15)
    if recent:
        table = [
            {
                "ID": r["id"],
                "Время": str(r["timestamp"])[:19].replace("T", " "),
                "Источник": r["username"] or r["user_id"],
                "Марка": str(r["brand"]).capitalize(),
                "Кузов": str(r["carbody"]).capitalize(),
                "Л.с.": int(r["horsepower"]),
                "Цена ($)": f"${r['predicted_price_usd']:,.0f}",
                "Цена (₽)": f"{r['predicted_price_rub']:,.0f} ₽",
                "Модель": r["model_name"],
            }
            for r in recent
        ]
        st.dataframe(pd.DataFrame(table), use_container_width=True, hide_index=True)
    else:
        st.info("История расчётов пока пуста.")

    st.subheader("Сравнение моделей: Python vs Loginom")
    metrics = service.get_metrics_summary()
    rev_names = {
        "random_forest": "Случайный лес (Random Forest)",
        "linear_regression": "Гребневая регрессия (Ridge)",
        "neural_network": "Нейронная сеть (MLP)",
        "knn": "Метод k-ближайших соседей (KNN)",
    }
    rows = []
    for key, label in rev_names.items():
        py_m = metrics.get(key, {})
        lg_m = LOGINOM_BENCHMARKS.get(key, {})
        rows.append(
            {
                "Модель": label,
                "R² (Python)": f"{py_m.get('r2', 0):.4f}",
                "R² (Loginom)": f"{lg_m.get('r2', 0):.4f}",
                "RMSE ($)": f"${py_m.get('rmse', 0):,.0f}",
                "MAPE (%)": f"{py_m.get('mape', 0):.2f}%",
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    with st.expander("Сведения о курсовой работе"):
        st.markdown(
            f"- **ВУЗ:** {UNIVERSITY_NAME}\n"
            f"- **Студент:** {STUDENT_NAME} ({STUDENT_GROUP})\n"
            f"- **Тема:** {COURSE_TOPIC}\n"
            f"- **Вариант:** №{COURSE_VARIANT}"
        )
