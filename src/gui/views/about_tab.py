"""Вкладка информации о курсовой работе, авторе и сравнительных метриках."""

import customtkinter as ctk
from src.config import STUDENT_NAME, STUDENT_GROUP, UNIVERSITY_NAME, COURSE_TOPIC, COURSE_VARIANT
from src.storage.repository import get_overall_stats


def build_about_tab(parent: ctk.CTkFrame) -> None:
    """Создает информационную панель сведений о проекте."""
    cont = ctk.CTkScrollableFrame(parent, fg_color="transparent")
    cont.pack(fill="both", expand=True, padx=4, pady=4)

    # Карточка студента
    s_card = ctk.CTkFrame(cont, corner_radius=10, fg_color=("#f1f5f9", "#1e293b"))
    s_card.pack(fill="x", padx=8, pady=6)
    ctk.CTkLabel(s_card, text="🎓 Сведения об авторе и курсовой работе", font=ctk.CTkFont(size=13, weight="bold"), text_color="#38bdf8").pack(anchor="w", padx=12, pady=(10, 4))
    info = (
        f"• ВУЗ: {UNIVERSITY_NAME} | Факультет: ФИТ | Кафедра: ПО\n"
        f"• Студент: {STUDENT_NAME} (группа {STUDENT_GROUP})\n"
        f"• Тема курсовой: {COURSE_TOPIC}\n"
        f"• Вариант задания: №{COURSE_VARIANT} | Руководитель: Корнеева Е.И."
    )
    ctk.CTkLabel(s_card, text=info, font=ctk.CTkFont(size=11), justify="left").pack(anchor="w", padx=12, pady=(0, 10))

    # Сравнительная таблица метрик
    t_card = ctk.CTkFrame(cont, corner_radius=10, fg_color=("#f1f5f9", "#1e293b"))
    t_card.pack(fill="x", padx=8, pady=6)
    ctk.CTkLabel(t_card, text="📊 Сравнение качества моделей: Python vs Loginom Studio", font=ctk.CTkFont(size=13, weight="bold"), text_color="#10b981").pack(anchor="w", padx=12, pady=(10, 4))

    grid = ctk.CTkFrame(t_card, fg_color=("#e2e8f0", "#0f172a"), corner_radius=8)
    grid.pack(fill="x", padx=12, pady=(0, 10))
    grid.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

    headers = ["Алгоритм", "R² (Python)", "R² (Loginom)", "RMSE ($)", "MAPE (%)"]
    for c, h in enumerate(headers):
        ctk.CTkLabel(grid, text=h, font=ctk.CTkFont(size=10, weight="bold"), text_color="#38bdf8").grid(row=0, column=c, padx=6, pady=4, sticky="ew")

    rows = [
        ("Случайный лес (Random Forest)", "0.9584", "0.9480", "$1,811", "9.11%"),
        ("Гребневая регрессия (Ridge)", "0.8980", "0.8812", "$2,837", "17.27%"),
        ("Нейросеть (MLP Regressor)", "0.8632", "0.8540", "$3,286", "19.05%"),
        ("Метод k-соседей (KNN)", "0.7757", "0.8250", "$4,208", "13.67%"),
    ]
    for r, r_data in enumerate(rows, 1):
        for c, val in enumerate(r_data):
            col = "#10b981" if c == 1 and r == 1 else "#cbd5e1"
            ctk.CTkLabel(grid, text=val, font=ctk.CTkFont(size=10), text_color=col).grid(row=r, column=c, padx=6, pady=2, sticky="ew")

    # База данных
    db_card = ctk.CTkFrame(cont, corner_radius=10, fg_color=("#f1f5f9", "#1e293b"))
    db_card.pack(fill="x", padx=8, pady=6)
    ctk.CTkLabel(db_card, text="💾 Статистика реляционной базы данных (SQLite)", font=ctk.CTkFont(size=13, weight="bold"), text_color="#f59e0b").pack(anchor="w", padx=12, pady=(10, 4))
    st = get_overall_stats()
    db_text = (
        f"• Всего расчетов в базе: {st.get('total_queries', 0)}\n"
        f"• Уникальных пользователей: {st.get('unique_users', 0)}\n"
        f"• Средняя стоимость: ${st.get('avg_predicted_price_usd', 0):,.0f}\n"
        f"• Популярная марка: {st.get('top_brand', 'toyota').capitalize()}"
    )
    ctk.CTkLabel(db_card, text=db_text, font=ctk.CTkFont(size=11), justify="left").pack(anchor="w", padx=12, pady=(0, 10))
