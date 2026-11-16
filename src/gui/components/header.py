"""Компонент верхней панели заголовка приложения."""

import customtkinter as ctk
from src.config import APP_NAME, STUDENT_NAME, STUDENT_GROUP, COURSE_VARIANT


def build_header(parent: ctk.CTk, on_toggle_theme) -> ctk.CTkSwitch:
    """Создает верхнюю панель заголовка со статусом и переключателем темы."""
    header = ctk.CTkFrame(parent, corner_radius=0, fg_color=("#1e293b", "#0f172a"))
    header.pack(fill="x", padx=0, pady=0)

    left = ctk.CTkFrame(header, fg_color="transparent")
    left.pack(side="left", padx=20, pady=10)
    ctk.CTkLabel(left, text=f"🚗 {APP_NAME}", font=ctk.CTkFont(size=20, weight="bold"), text_color="#38bdf8").pack(anchor="w")
    ctk.CTkLabel(left, text="Интеллектуальная система оценки стоимости авто на базе Machine Learning", font=ctk.CTkFont(size=11), text_color="#94a3b8").pack(anchor="w")

    right = ctk.CTkFrame(header, fg_color="transparent")
    right.pack(side="right", padx=20, pady=10)

    badge_text = f"🎓 {STUDENT_NAME} • {STUDENT_GROUP} • Вариант {COURSE_VARIANT}"
    badge = ctk.CTkLabel(right, text=badge_text, font=ctk.CTkFont(size=11, weight="bold"), fg_color=("#334155", "#1e293b"), corner_radius=8, padx=12, pady=4, text_color="#e2e8f0")
    badge.pack(side="left", padx=(0, 15))

    switch = ctk.CTkSwitch(right, text="Темная тема", font=ctk.CTkFont(size=12), command=on_toggle_theme, onvalue="Dark", offvalue="Light")
    switch.select()
    switch.pack(side="right")
    return switch
