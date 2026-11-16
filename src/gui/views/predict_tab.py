"""Вкладка прогнозирования стоимости автомобиля."""

import customtkinter as ctk
from src.gui.views.predict_form import build_predict_form
from src.gui.views.predict_result import build_predict_result_card


def build_predict_tab(parent: ctk.CTkFrame, app) -> None:
    """Создает двухколоночный интерфейс вкладки прогноза."""
    container = ctk.CTkFrame(parent, fg_color="transparent")
    container.pack(fill="both", expand=True, padx=4, pady=4)
    container.grid_columnconfigure(0, weight=6)
    container.grid_columnconfigure(1, weight=5)
    container.grid_rowconfigure(0, weight=1)

    build_predict_form(container, app)
    build_predict_result_card(container, app)
