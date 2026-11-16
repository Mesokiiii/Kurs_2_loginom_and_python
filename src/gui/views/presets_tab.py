"""Вкладка готовых типовых пресетов автомобилей."""

from typing import Dict, Any
import customtkinter as ctk
from src.config import CAR_PRESETS


def build_presets_tab(parent: ctk.CTkFrame, app) -> None:
    """Создает сетку карточек типовых конфигураций."""
    cont = ctk.CTkFrame(parent, fg_color="transparent")
    cont.pack(fill="both", expand=True, padx=4, pady=4)

    ctk.CTkLabel(cont, text="Готовые типовые пресеты для быстрой проверки и демонстрации:",
                 font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=8, pady=(4, 8))

    grid = ctk.CTkFrame(cont, fg_color="transparent")
    grid.pack(fill="both", expand=True, padx=4, pady=4)
    grid.grid_columnconfigure((0, 1), weight=1)
    grid.grid_rowconfigure((0, 1), weight=1)

    icons = ["🚗", "🚘", "🏎️", "🚙"]
    for idx, (p_name, p_data) in enumerate(CAR_PRESETS.items()):
        _build_preset_card(grid, idx // 2, idx % 2, icons[idx % len(icons)], p_name, p_data, app)


def _build_preset_card(grid: ctk.CTkFrame, row: int, col: int, icon: str, name: str, data: Dict[str, Any], app) -> None:
    """Создает отдельную карточку пресета."""
    card = ctk.CTkFrame(grid, corner_radius=10, fg_color=("#f1f5f9", "#1e293b"), border_width=1, border_color=("#cbd5e1", "#334155"))
    card.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")

    ctk.CTkLabel(card, text=f"{icon} {name}", font=ctk.CTkFont(size=13, weight="bold"), text_color="#38bdf8", anchor="w").pack(fill="x", padx=12, pady=(10, 2))
    ctk.CTkLabel(card, text=data.get("description", ""), font=ctk.CTkFont(size=11), text_color="#94a3b8", anchor="w").pack(fill="x", padx=12, pady=(0, 6))

    specs = (
        f"• {data['brand'].capitalize()} ({data['carbody'].capitalize()})\n"
        f"• Мощность: {data['horsepower']} л.с. | Объем: {data['enginesize']} cu in\n"
        f"• Масса: {data['curbweight']} lbs | Расход: {data['citympg']}/{data['highwaympg']} MPG\n"
        f"• Топливо: {data['fueltype'].capitalize()} ({data['aspiration']})"
    )
    ctk.CTkLabel(card, text=specs, font=ctk.CTkFont(size=11), justify="left", anchor="w").pack(fill="x", padx=12, pady=2)

    btn_box = ctk.CTkFrame(card, fg_color="transparent")
    btn_box.pack(fill="x", padx=12, pady=(8, 10))

    btn_load = ctk.CTkButton(btn_box, text="Загрузить в форму", font=ctk.CTkFont(size=11, weight="bold"),
                             fg_color="#334155", hover_color="#475569", height=30,
                             command=lambda p=data: app._load_preset_to_form(p))
    btn_load.pack(side="left", expand=True, fill="x", padx=(0, 4))

    btn_eval = ctk.CTkButton(btn_box, text="⚡ Оценить", font=ctk.CTkFont(size=11, weight="bold"),
                             fg_color="#2563eb", hover_color="#1d4ed8", height=30,
                             command=lambda p=data: app._load_preset_to_form(p))
    btn_eval.pack(side="right", expand=True, fill="x", padx=(4, 0))
