"""Главный модуль веб-интерфейса на Streamlit."""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pandas as pd
import streamlit as st

from src.config import APP_NAME, APP_VERSION, COURSE_VARIANT, RAW_DATA_PATH
from src.data.cleaner import clean_car_dataframe
from src.models.service import ModelService
from src.web.predict_page import render_predict_page
from src.web.presets_page import render_presets_page
from src.web.olap_page import render_olap_page
from src.web.history_page import render_history_page


@st.cache_resource
def get_service() -> ModelService:
    return ModelService()


@st.cache_data
def get_market_data() -> pd.DataFrame:
    if not RAW_DATA_PATH.exists():
        return pd.DataFrame()
    return clean_car_dataframe(pd.read_csv(RAW_DATA_PATH))


def main() -> None:
    st.set_page_config(
        page_title=f"{APP_NAME} v{APP_VERSION}",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    sections = [
        "Прогнозирование",
        "Пресеты авто",
        "Аналитика (OLAP)",
        "История и о проекте",
    ]
    if "section" not in st.session_state:
        st.session_state["section"] = sections[0]

    with st.sidebar:
        st.title(APP_NAME)
        st.caption(f"Версия {APP_VERSION} · Вариант {COURSE_VARIANT}")
        st.divider()
        section = st.radio("Разделы", sections, key="section")

    service = get_service()

    if section == "Прогнозирование":
        render_predict_page(service)
    elif section == "Пресеты авто":
        render_presets_page(service)
    elif section == "Аналитика (OLAP)":
        render_olap_page(get_market_data())
    else:
        render_history_page(service)


if __name__ == "__main__":
    main()
