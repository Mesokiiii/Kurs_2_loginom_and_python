"""Вкладка интерактивного многомерного анализа данных (OLAP)."""

import customtkinter as ctk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from src.gui.components.kpi_card import create_kpi_card
from src.gui.views.olap_charts import (
    render_brand_top10, render_body_comparison, render_hp_scatter, render_fuel_pie,
)


def build_olap_tab(parent: ctk.CTkFrame, app) -> None:
    """Создает элементы вкладки OLAP-аналитики."""
    cont = ctk.CTkFrame(parent, fg_color="transparent")
    cont.pack(fill="both", expand=True, padx=4, pady=4)

    # Верхние KPI карточки
    kpis = ctk.CTkFrame(cont, fg_color="transparent")
    kpis.pack(fill="x", pady=(0, 6))
    kpis.grid_columnconfigure((0, 1, 2, 3), weight=1)
    create_kpi_card(kpis, 0, "205", "Автомобилей в базе", "#38bdf8")
    create_kpi_card(kpis, 1, "$13,277", "Средняя стоимость", "#10b981")
    create_kpi_card(kpis, 2, "$10,295", "Медиана рынка", "#f59e0b")
    create_kpi_card(kpis, 3, "$45,400", "Максимум (Люкс)", "#a855f7")

    # Панель выбора среза
    ctrl = ctk.CTkFrame(cont, corner_radius=8, fg_color=("#f1f5f9", "#1e293b"))
    ctrl.pack(fill="x", pady=(0, 6))
    ctk.CTkLabel(ctrl, text="OLAP-срез рынка:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=12, pady=6)

    app.olap_options = [
        "Средняя цена по маркам (Топ-10)",
        "Цены по типам кузова (Boxplot / Bar)",
        "Зависимость: Мощность vs Цена",
        "Распределение по типу топлива",
    ]
    app.olap_menu = ctk.CTkOptionMenu(ctrl, values=app.olap_options, width=320, fg_color="#2563eb", button_color="#1d4ed8",
                                      command=app._update_olap_chart)
    app.olap_menu.set(app.olap_options[0])
    app.olap_menu.pack(side="left", padx=8, pady=6)

    # Холст Matplotlib
    chart_card = ctk.CTkFrame(cont, corner_radius=10, fg_color=("#1e293b", "#0f172a"))
    chart_card.pack(fill="both", expand=True, pady=(0, 4))

    app.fig = Figure(figsize=(8.5, 4.0), dpi=100, facecolor="#0f172a")
    app.ax = app.fig.add_subplot(111)
    app.ax.set_facecolor("#1e293b")

    app.canvas = FigureCanvasTkAgg(app.fig, master=chart_card)
    app.canvas.get_tk_widget().pack(fill="both", expand=True, padx=6, pady=6)

    app.olap_text = ctk.CTkLabel(cont, text="", font=ctk.CTkFont(size=11), text_color="#94a3b8", justify="left", anchor="w")
    app.olap_text.pack(fill="x", padx=8, pady=(0, 4))
    update_olap_chart_view(app, app.olap_options[0])


def update_olap_chart_view(app, selection: str) -> None:
    """Отрисовка выбранного графика на холсте."""
    app.ax.clear()
    df = getattr(app, "market_df", None)
    if df is None or df.empty:
        app.ax.text(0.5, 0.5, "Данные недоступны", color="white", ha="center")
        app.canvas.draw()
        return

    app.ax.set_facecolor("#1e293b")
    app.ax.tick_params(colors="#cbd5e1", labelsize=9)
    for spine in app.ax.spines.values():
        spine.set_color("#334155")

    if "Топ-10" in selection:
        render_brand_top10(app.ax, df, app.olap_text)
    elif "кузова" in selection:
        render_body_comparison(app.ax, df, app.olap_text)
    elif "Мощность" in selection:
        render_hp_scatter(app.ax, app.fig, df, app.olap_text)
    else:
        render_fuel_pie(app.ax, df, app.olap_text)

    app.fig.tight_layout()
    app.canvas.draw()
