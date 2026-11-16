"""Форма ввода параметров автомобиля для вкладки прогноза."""

import customtkinter as ctk
from src.config import ALLOWED_BRANDS, MODEL_NAMES
from src.gui.components.slider_field import create_slider_field


def build_predict_form(parent: ctk.CTkFrame, app) -> None:
    """Создает форму с выпадающими списками и слайдерами."""
    form = ctk.CTkScrollableFrame(parent, label_text="Параметры автомобиля", label_font=ctk.CTkFont(size=14, weight="bold"),
                                  corner_radius=10, border_width=1, border_color=("#cbd5e1", "#334155"))
    form.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=0)

    # Выбор модели
    m_card = ctk.CTkFrame(form, fg_color=("#f1f5f9", "#1e293b"), corner_radius=8)
    m_card.pack(fill="x", padx=8, pady=(4, 8))
    ctk.CTkLabel(m_card, text="Алгоритм прогнозирования (ML):", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=10, pady=(6, 2))

    app.model_menu = ctk.CTkOptionMenu(m_card, values=MODEL_NAMES, fg_color="#2563eb", button_color="#1d4ed8",
                                       command=lambda _: app._on_model_select_change())
    app.model_menu.set(MODEL_NAMES[0])
    app.model_menu.pack(fill="x", padx=10, pady=(0, 4))
    app.lbl_model_hint = ctk.CTkLabel(m_card, text="⚡ Точность: R² = 0.958, MAPE = 9.1% (Случайный лес)",
                                      font=ctk.CTkFont(size=11), text_color="#10b981")
    app.lbl_model_hint.pack(anchor="w", padx=10, pady=(0, 6))

    # Категориальные признаки
    cat_card = ctk.CTkFrame(form, fg_color=("#f8fafc", "#1e293b"), corner_radius=8)
    cat_card.pack(fill="x", padx=8, pady=4)
    grid = ctk.CTkFrame(cat_card, fg_color="transparent")
    grid.pack(fill="x", padx=6, pady=4)
    grid.grid_columnconfigure((0, 1), weight=1)

    app.brand_menu = ctk.CTkOptionMenu(grid, values=[b.capitalize() for b in ALLOWED_BRANDS])
    app.brand_menu.set("Toyota")
    app.brand_menu.grid(row=0, column=0, padx=4, pady=4, sticky="ew")

    app.body_menu = ctk.CTkOptionMenu(grid, values=["Sedan", "Hatchback", "Wagon", "Hardtop", "Convertible"])
    app.body_menu.set("Sedan")
    app.body_menu.grid(row=0, column=1, padx=4, pady=4, sticky="ew")

    app.fuel_menu = ctk.CTkOptionMenu(grid, values=["Gas (Бензин)", "Diesel (Дизель)"])
    app.fuel_menu.set("Gas (Бензин)")
    app.fuel_menu.grid(row=1, column=0, padx=4, pady=4, sticky="ew")

    app.asp_menu = ctk.CTkOptionMenu(grid, values=["Std (Атмосферный)", "Turbo (Турбо)"])
    app.asp_menu.set("Std (Атмосферный)")
    app.asp_menu.grid(row=1, column=1, padx=4, pady=4, sticky="ew")

    app.drive_menu = ctk.CTkOptionMenu(grid, values=["FWD (Передний)", "RWD (Задний)", "4WD (Полный)"])
    app.drive_menu.set("FWD (Передний)")
    app.drive_menu.grid(row=2, column=0, columnspan=2, padx=4, pady=4, sticky="ew")

    # Числовые характеристики
    num_card = ctk.CTkFrame(form, fg_color=("#f8fafc", "#1e293b"), corner_radius=8)
    num_card.pack(fill="x", padx=8, pady=4)
    create_slider_field(num_card, app, "horsepower", "Мощность двигателя (л.с.):", 48, 288, 104, 1, "л.с.")
    create_slider_field(num_card, app, "enginesize", "Объем двигателя (куб. дюймы):", 61, 326, 120, 1, "cu in")
    create_slider_field(num_card, app, "curbweight", "Снаряженная масса (фунты):", 1488, 4066, 2414, 10, "lbs")
    create_slider_field(num_card, app, "citympg", "Расход топлива в городе (MPG):", 13, 49, 25, 1, "MPG")
    create_slider_field(num_card, app, "highwaympg", "Расход на трассе (MPG):", 16, 54, 30, 1, "MPG")

    # Кнопка расчета
    btn = ctk.CTkButton(form, text="⚡ Рассчитать рыночную стоимость", font=ctk.CTkFont(size=14, weight="bold"),
                        fg_color="#2563eb", hover_color="#1d4ed8", height=42, corner_radius=8,
                        command=app._on_predict_click)
    btn.pack(fill="x", padx=8, pady=(10, 14))
