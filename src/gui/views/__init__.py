"""Пакет представлений (вкладок) графического интерфейса."""

from src.gui.views.predict_tab import build_predict_tab
from src.gui.views.olap_tab import build_olap_tab, update_olap_chart_view
from src.gui.views.presets_tab import build_presets_tab
from src.gui.views.about_tab import build_about_tab

__all__ = ["build_predict_tab", "build_olap_tab", "update_olap_chart_view", "presets_tab", "build_about_tab"]
