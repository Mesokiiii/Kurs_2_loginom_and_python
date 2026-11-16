"""Карточка отображения результатов интеллектуальной оценки автомобиля."""

import customtkinter as ctk


def build_predict_result_card(parent: ctk.CTkFrame, app) -> None:
    """Создает карточку отображения цены, перцентиля и доверительного интервала."""
    res_frame = ctk.CTkFrame(parent, corner_radius=10, border_width=1, border_color=("#cbd5e1", "#334155"))
    res_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=0)

    ctk.CTkLabel(res_frame, text="Результаты интеллектуальной оценки", font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", padx=16, pady=(12, 6))

    # Главная карточка цены
    price_box = ctk.CTkFrame(res_frame, fg_color=("#1e293b", "#0f172a"), corner_radius=12, border_width=2, border_color="#38bdf8")
    price_box.pack(fill="x", padx=14, pady=4)

    ctk.CTkLabel(price_box, text="РЕКОМЕНДУЕМАЯ РЫНОЧНАЯ СТОИМОСТЬ", font=ctk.CTkFont(size=10, weight="bold"), text_color="#94a3b8").pack(padx=16, pady=(10, 0))
    app.lbl_price_usd = ctk.CTkLabel(price_box, text="$0", font=ctk.CTkFont(size=36, weight="bold"), text_color="#38bdf8")
    app.lbl_price_usd.pack(padx=16, pady=(2, 2))

    app.lbl_price_rub = ctk.CTkLabel(price_box, text="~0 руб. (курс 93.5 ₽/$)", font=ctk.CTkFont(size=14, weight="bold"), text_color="#cbd5e1")
    app.lbl_price_rub.pack(padx=16, pady=(0, 4))

    app.lbl_category_badge = ctk.CTkLabel(price_box, text="[ Масс-маркет ]", font=ctk.CTkFont(size=11, weight="bold"),
                                         fg_color="#1e3a8a", text_color="#93c5fd", corner_radius=6, padx=12, pady=3)
    app.lbl_category_badge.pack(pady=(0, 10))

    # Положение на рынке
    pos_box = ctk.CTkFrame(res_frame, fg_color=("#f1f5f9", "#1e293b"), corner_radius=8)
    pos_box.pack(fill="x", padx=14, pady=4)
    ctk.CTkLabel(pos_box, text="Положение в распределении рынка цен:", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=12, pady=(6, 2))

    app.market_progress = ctk.CTkProgressBar(pos_box, height=10, corner_radius=5, progress_color="#38bdf8")
    app.market_progress.pack(fill="x", padx=12, pady=4)
    app.market_progress.set(0.5)

    lbls = ctk.CTkFrame(pos_box, fg_color="transparent")
    lbls.pack(fill="x", padx=12, pady=(0, 6))
    ctk.CTkLabel(lbls, text="Эконом ($5k)", font=ctk.CTkFont(size=9), text_color="#94a3b8").pack(side="left")
    ctk.CTkLabel(lbls, text="Медиана ($10.3k)", font=ctk.CTkFont(size=9), text_color="#94a3b8").pack(side="left", expand=True)
    ctk.CTkLabel(lbls, text="Люкс ($45k+)", font=ctk.CTkFont(size=9), text_color="#94a3b8").pack(side="right")

    # Подробности
    details = ctk.CTkFrame(res_frame, corner_radius=8, fg_color=("#f8fafc", "#1e293b"))
    details.pack(fill="both", expand=True, padx=14, pady=4)

    app.lbl_ci = ctk.CTkLabel(details, text="95% Доверительный интервал: —", font=ctk.CTkFont(size=11, weight="bold"), anchor="w")
    app.lbl_ci.pack(fill="x", padx=12, pady=(8, 2))
    app.lbl_category = ctk.CTkLabel(details, text="Сегмент рынка: —", font=ctk.CTkFont(size=11), anchor="w")
    app.lbl_category.pack(fill="x", padx=12, pady=2)
    app.lbl_percentile = ctk.CTkLabel(details, text="Перцентиль: —", font=ctk.CTkFont(size=11), anchor="w")
    app.lbl_percentile.pack(fill="x", padx=12, pady=2)
    app.lbl_comparison = ctk.CTkLabel(details, text="Сравнение с рынком: —", font=ctk.CTkFont(size=11), anchor="w")
    app.lbl_comparison.pack(fill="x", padx=12, pady=2)
    app.lbl_model_used = ctk.CTkLabel(details, text="Модель: —", font=ctk.CTkFont(size=11), text_color="#64748b", anchor="w")
    app.lbl_model_used.pack(fill="x", padx=12, pady=(4, 6))

    app.lbl_db_status = ctk.CTkLabel(res_frame, text="● Запрос успешно сохранен в базе данных SQLite",
                                     font=ctk.CTkFont(size=10), text_color="#10b981")
    app.lbl_db_status.pack(side="bottom", pady=8)
