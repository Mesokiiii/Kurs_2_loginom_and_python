"""Компонент карточки сводной метрики (KPI)."""

import customtkinter as ctk


def create_kpi_card(parent: ctk.CTkBaseClass, col: int, val: str, title: str, color: str) -> None:
    """Создает мини-карточку со статистической метрикой."""
    card = ctk.CTkFrame(parent, corner_radius=10, fg_color=("#f1f5f9", "#1e293b"))
    card.grid(row=0, column=col, sticky="ew", padx=4, pady=2)
    ctk.CTkLabel(card, text=val, font=ctk.CTkFont(size=20, weight="bold"), text_color=color).pack(padx=10, pady=(6, 0))
    ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=10), text_color="#94a3b8").pack(padx=10, pady=(0, 6))
