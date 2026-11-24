"""Раздел прогнозирования цены автомобиля."""

from typing import Dict, Any
import pandas as pd
import streamlit as st

from src.config import (
    ALLOWED_BRANDS,
    ALLOWED_BODIES,
    ALLOWED_FUELS,
    ALLOWED_ASPIRATIONS,
    ALLOWED_DRIVES,
    FEATURE_DEFAULTS,
    FEATURE_RANGES,
    MODEL_NAMES,
    USD_TO_RUB_RATE,
)
from src.models.service import ModelService
from src.storage.repository import log_prediction


def _init_form_state() -> None:
    """Инициализирует значения формы по умолчанию."""
    defaults = {
        "form_model": MODEL_NAMES[0],
        "form_brand": FEATURE_DEFAULTS["brand"],
        "form_carbody": FEATURE_DEFAULTS["carbody"],
        "form_fueltype": FEATURE_DEFAULTS["fueltype"],
        "form_aspiration": FEATURE_DEFAULTS["aspiration"],
        "form_drivewheel": FEATURE_DEFAULTS["drivewheel"],
        "form_horsepower": float(FEATURE_DEFAULTS["horsepower"]),
        "form_enginesize": float(FEATURE_DEFAULTS["enginesize"]),
        "form_curbweight": float(FEATURE_DEFAULTS["curbweight"]),
        "form_citympg": float(FEATURE_DEFAULTS["citympg"]),
        "form_highwaympg": float(FEATURE_DEFAULTS["highwaympg"]),
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def apply_preset_to_state(preset: Dict[str, Any]) -> None:
    """Переносит параметры пресета в состояние формы и открывает раздел прогноза."""
    st.session_state["form_brand"] = preset["brand"]
    st.session_state["form_carbody"] = preset["carbody"]
    st.session_state["form_fueltype"] = preset["fueltype"]
    st.session_state["form_aspiration"] = preset["aspiration"]
    st.session_state["form_drivewheel"] = preset["drivewheel"]
    for field in ("horsepower", "enginesize", "curbweight", "citympg", "highwaympg"):
        st.session_state[f"form_{field}"] = float(preset[field])
    st.session_state["section"] = "Прогнозирование"


def render_predict_page(service: ModelService) -> None:
    """Отрисовывает раздел прогнозирования стоимости автомобиля."""
    _init_form_state()
    st.header("Прогнозирование цены автомобиля")

    col_form, col_res = st.columns([1.05, 1.15], gap="large")

    with col_form:
        with st.container(border=True):
            st.subheader("Параметры автомобиля")
            model_name = st.selectbox("Модель ML", MODEL_NAMES, key="form_model")

            c1, c2 = st.columns(2)
            with c1:
                brand = st.selectbox("Марка", ALLOWED_BRANDS, format_func=str.capitalize, key="form_brand")
                fuel = st.selectbox("Топливо", ALLOWED_FUELS, format_func=lambda x: "Бензин (gas)" if x == "gas" else "Дизель (diesel)", key="form_fueltype")
                drive = st.selectbox("Привод", ALLOWED_DRIVES, format_func=str.upper, key="form_drivewheel")
            with c2:
                carbody = st.selectbox("Тип кузова", ALLOWED_BODIES, format_func=str.capitalize, key="form_carbody")
                aspiration = st.selectbox("Наддув", ALLOWED_ASPIRATIONS, format_func=lambda x: "Атмосферный (std)" if x == "std" else "Турбо (turbo)", key="form_aspiration")

            hp_min, hp_max, hp_step = FEATURE_RANGES["horsepower"]
            hp = st.slider("Мощность (л.с.)", hp_min, hp_max, step=hp_step, key="form_horsepower")

            eng_min, eng_max, eng_step = FEATURE_RANGES["enginesize"]
            eng = st.slider("Объем двигателя (cu in)", eng_min, eng_max, step=eng_step, key="form_enginesize")

            w_min, w_max, w_step = FEATURE_RANGES["curbweight"]
            weight = st.slider("Снаряженная масса (lbs)", w_min, w_max, step=w_step, key="form_curbweight")

            c3, c4 = st.columns(2)
            with c3:
                cm_min, cm_max, cm_step = FEATURE_RANGES["citympg"]
                city_mpg = st.slider("Расход город (MPG)", cm_min, cm_max, step=cm_step, key="form_citympg")
            with c4:
                hm_min, hm_max, hm_step = FEATURE_RANGES["highwaympg"]
                hwy_mpg = st.slider("Расход трасса (MPG)", hm_min, hm_max, step=hm_step, key="form_highwaympg")

            save_clicked = st.button("Сохранить расчёт в историю", type="primary", use_container_width=True)

    features = {
        "brand": brand,
        "carbody": carbody,
        "fueltype": fuel,
        "aspiration": aspiration,
        "drivewheel": drive,
        "horsepower": hp,
        "enginesize": eng,
        "curbweight": weight,
        "citympg": city_mpg,
        "highwaympg": hwy_mpg,
    }

    res = service.predict(features, model_selection=model_name)

    if save_clicked:
        rec_id = log_prediction("web_user", res.price_usd, res.price_rub, res.model_name, features, "Streamlit_Web")
        st.toast(f"Расчёт сохранён в SQLite (ID: {rec_id})")

    with col_res:
        with st.container(border=True):
            st.subheader("Результат оценки")
            m1, m2, m3 = st.columns(3)
            m1.metric("Цена ($)", f"${res.price_usd:,.0f}")
            m2.metric(f"Цена (₽, курс {USD_TO_RUB_RATE})", f"{res.price_rub:,.0f} ₽")
            m3.metric("Вероятность цены", f"{res.price_probability:.1f}%", help="Вероятность попадания реальной цены в диапазон ±15% от прогноза")

            st.caption(f"Сегмент: **{res.market_category}** · {res.comparison_to_average}")
            st.progress(min(1.0, max(0.0, res.market_percentile / 100.0)), text=f"Дороже {res.market_percentile:.1f}% автомобилей на рынке")

            st.markdown(
                f"- **95% доверительный интервал:** `${res.ci_lower_usd:,.0f}` — `${res.ci_upper_usd:,.0f}` "
                f"(`{res.ci_lower_rub:,.0f}` — `{res.ci_upper_rub:,.0f} ₽`)\n"
                f"- **Выбранная модель:** {res.model_name}"
            )

        with st.container(border=True):
            st.subheader("Сравнение всех моделей (цена + вероятность)")
            all_preds = service.predict_all_models(features)
            rows = [
                {
                    "Модель": p.model_name,
                    "Цена ($)": f"${p.price_usd:,.0f}",
                    "Цена (₽)": f"{p.price_rub:,.0f} ₽",
                    "Вероятность (%)": f"{p.price_probability:.1f}%",
                    "95% интервал ($)": f"${p.ci_lower_usd:,.0f} – ${p.ci_upper_usd:,.0f}",
                }
                for p in all_preds
            ]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
