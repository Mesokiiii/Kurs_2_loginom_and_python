"""Действия обновления интерфейса результатами расчета и пресетами."""

from typing import Dict, Any
from src.models.model_service import PredictionResult
from src.storage.repository import log_prediction


def apply_prediction_result(app, res: PredictionResult, feats: Dict[str, Any]) -> None:
    """Обновляет элементы отображения карточки результатов прогноза."""
    app.lbl_price_usd.configure(text=f"${res.price_usd:,.0f}")
    app.lbl_price_rub.configure(text=f"~{res.price_rub:,.0f} руб. (курс 93.5)")
    app.lbl_ci.configure(text=f"95% Доверительный интервал:  ${res.ci_lower_usd:,.0f} ... ${res.ci_upper_usd:,.0f}")
    app.lbl_category.configure(text=f"Сегмент рынка:  {res.market_category}")
    app.lbl_percentile.configure(text=f"Положение на рынке:  дороже {res.market_percentile:.1f}% авто")
    app.lbl_comparison.configure(text=f"Сравнение со средним:  {res.comparison_to_average}")
    app.lbl_model_used.configure(text=f"Модель:  {res.model_name}")
    app.market_progress.set(min(1.0, max(0.0, res.market_percentile / 100.0)))
    rec_id = log_prediction("gui_user", res.price_usd, res.price_rub, res.model_name, feats, "Desktop_GUI")
    app.lbl_db_status.configure(text=f"● Запрос успешно сохранен в базе данных SQLite (ID: {rec_id})")


def apply_preset(app, preset: Dict[str, Any]) -> None:
    """Заполняет поля формы характеристиками выбранного пресета."""
    app.brand_menu.set(preset["brand"].capitalize())
    app.body_menu.set(preset["carbody"].capitalize())
    app.fuel_menu.set("Gas (Бензин)" if preset["fueltype"] == "gas" else "Diesel (Дизель)")
    app.asp_menu.set("Turbo (Турбо)" if preset["aspiration"] == "turbo" else "Std (Атмосферный)")
    for k in ["horsepower", "enginesize", "curbweight", "citympg", "highwaympg"]:
        if k in preset and k in app.slider_vars:
            val = float(preset[k])
            app.slider_vars[k].set(val)
            if k in app.entry_widgets:
                app.entry_widgets[k].delete(0, "end")
                app.entry_widgets[k].insert(0, f"{val:.0f}")
    app.tabview.set("  🎯 Прогнозирование цены  ")
    app._on_predict_click()
