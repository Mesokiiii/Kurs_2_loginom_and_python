"""Главное окно приложения на CustomTkinter."""

from typing import Dict, Any, Optional
import customtkinter as ctk
import pandas as pd
from src.config import APP_NAME, APP_VERSION, COURSE_VARIANT, RAW_DATA_PATH
from src.data.preprocessor import clean_car_dataframe
from src.models.model_service import ModelService
from src.gui.components import build_header
from src.gui.views import build_predict_tab, build_olap_tab, update_olap_chart_view, build_presets_tab, build_about_tab
from src.gui.views.predict_action import apply_prediction_result, apply_preset

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class CarPriceApp(ctk.CTk):
    """Главный класс графического интерфейса пользователя."""

    def __init__(self, service: Optional[ModelService] = None) -> None:
        super().__init__()
        self.service = service or ModelService()
        self.title(f"{APP_NAME} v{APP_VERSION} — Вариант {COURSE_VARIANT}")
        self.geometry("1200x820")
        self.minsize(1050, 720)

        self._load_market_data()
        self.slider_vars: Dict[str, ctk.DoubleVar] = {}
        self.entry_widgets: Dict[str, ctk.CTkEntry] = {}

        self.theme_switch = build_header(self, self._toggle_theme)
        self.tabview = ctk.CTkTabview(self, corner_radius=10, segmented_button_selected_color="#2563eb")
        self.tabview.pack(fill="both", expand=True, padx=14, pady=(6, 12))

        self.tab_predict = self.tabview.add("  🎯 Прогнозирование цены  ")
        self.tab_olap = self.tabview.add("  📊 OLAP Анализ рынка  ")
        self.tab_presets = self.tabview.add("  ⚡ Быстрые пресеты  ")
        self.tab_about = self.tabview.add("  ℹ️ О программе  ")

        build_predict_tab(self.tab_predict, self)
        build_olap_tab(self.tab_olap, self)
        build_presets_tab(self.tab_presets, self)
        build_about_tab(self.tab_about)
        self._on_predict_click()

    def _load_market_data(self) -> None:
        try:
            self.market_df = clean_car_dataframe(pd.read_csv(RAW_DATA_PATH))
        except Exception:
            self.market_df = pd.DataFrame()

    def _toggle_theme(self) -> None:
        mode = "Dark" if self.theme_switch.get() == "Dark" else "Light"
        ctk.set_appearance_mode(mode)
        self.theme_switch.configure(text="Темная тема" if mode == "Dark" else "Светлая тема")

    def _on_model_select_change(self) -> None:
        self._on_predict_click()

    def _collect_inputs(self) -> Dict[str, Any]:
        fuel = "gas" if "gas" in self.fuel_menu.get().lower() else "diesel"
        asp = "turbo" if "turbo" in self.asp_menu.get().lower() else "std"
        dr = "4wd" if "4wd" in self.drive_menu.get().lower() else ("rwd" if "rwd" in self.drive_menu.get().lower() else "fwd")
        return {
            "brand": self.brand_menu.get().lower(), "carbody": self.body_menu.get().lower(),
            "fueltype": fuel, "aspiration": asp, "drivewheel": dr,
            "horsepower": float(self.slider_vars["horsepower"].get()),
            "enginesize": float(self.slider_vars["enginesize"].get()),
            "curbweight": float(self.slider_vars["curbweight"].get()),
            "citympg": float(self.slider_vars["citympg"].get()),
            "highwaympg": float(self.slider_vars["highwaympg"].get()),
        }

    def _on_predict_click(self) -> None:
        feats = self._collect_inputs()
        res = self.service.predict(feats, model_selection=self.model_menu.get())
        apply_prediction_result(self, res, feats)

    def _load_preset_to_form(self, preset: Dict[str, Any]) -> None:
        apply_preset(self, preset)

    def _update_olap_chart(self, selection: str) -> None:
        update_olap_chart_view(self, selection)


def launch_gui() -> None:
    CarPriceApp().mainloop()


if __name__ == "__main__":
    launch_gui()
