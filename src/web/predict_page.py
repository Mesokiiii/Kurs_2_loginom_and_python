"""Раздел прогнозирования цены автомобиля."""

from typing import Dict, Any, Tuple
import pandas as pd
import streamlit as st

from src.config import (
    ALLOWED_BRANDS,
    ALLOWED_BODIES,
    ALLOWED_FUELS,
    ALLOWED_ASPIRATIONS,
    ALLOWED_DRIVES,
    ASPIRATION_LABELS,
    BODY_LABELS,
    DRIVE_LABELS,
    FEATURE_DEFAULTS,
    FEATURE_RANGES,
    FUEL_LABELS,
    MODEL_NAMES,
    format_model_with_quality,
    format_rub,
)
from src.models.confidence import describe_price_probability
from src.models.service import ModelService
from src.storage.repository import log_prediction

_NUMERIC_FIELDS: Tuple[str, ...] = (
    "horsepower",
    "enginesize",
    "curbweight",
    "citympg",
    "highwaympg",
)


def _form_defaults() -> Dict[str, Any]:
    defaults: Dict[str, Any] = {
        "form_model": MODEL_NAMES[0],
        "form_brand": FEATURE_DEFAULTS["brand"],
        "form_carbody": FEATURE_DEFAULTS["carbody"],
        "form_fueltype": FEATURE_DEFAULTS["fueltype"],
        "form_aspiration": FEATURE_DEFAULTS["aspiration"],
        "form_drivewheel": FEATURE_DEFAULTS["drivewheel"],
    }
    for field in _NUMERIC_FIELDS:
        val = float(FEATURE_DEFAULTS[field])
        defaults[f"form_{field}"] = val
        defaults[f"form_{field}_num"] = val
    return defaults


def _init_form_state() -> None:
    """Инициализирует значения формы по умолчанию."""
    for key, val in _form_defaults().items():
        if key not in st.session_state:
            st.session_state[key] = val


def reset_form_state() -> None:
    """Сбрасывает все параметры формы к значениям по умолчанию."""
    for key, val in _form_defaults().items():
        st.session_state[key] = val


def _sync_from_slider(field: str) -> None:
    st.session_state[f"form_{field}_num"] = float(st.session_state[f"form_{field}"])


def _sync_from_number(field: str) -> None:
    st.session_state[f"form_{field}"] = float(st.session_state[f"form_{field}_num"])


def apply_preset_to_state(preset: Dict[str, Any]) -> None:
    """Переносит параметры пресета в состояние формы и открывает раздел прогноза."""
    st.session_state["form_brand"] = preset["brand"]
    st.session_state["form_carbody"] = preset["carbody"]
    st.session_state["form_fueltype"] = preset["fueltype"]
    st.session_state["form_aspiration"] = preset["aspiration"]
    st.session_state["form_drivewheel"] = preset["drivewheel"]
    for field in _NUMERIC_FIELDS:
        val = float(preset[field])
        st.session_state[f"form_{field}"] = val
        st.session_state[f"form_{field}_num"] = val
    st.session_state["section"] = "Прогнозирование"


def _bounded_numeric_input(field: str, label: str, unit: str) -> float:
    """Отрисовывает синхронизированную пару: ползунок + точное поле ввода с ограничителем."""
    min_val, max_val, step = FEATURE_RANGES[field]
    c_slider, c_num = st.columns([2.2, 1.0], gap="small")
    with c_slider:
        st.slider(
            f"{label} ({unit})",
            min_value=float(min_val),
            max_value=float(max_val),
            step=float(step),
            key=f"form_{field}",
            on_change=_sync_from_slider,
            args=(field,),
        )
    with c_num:
        st.number_input(
            f"Точно ({unit})",
            min_value=float(min_val),
            max_value=float(max_val),
            step=float(step),
            key=f"form_{field}_num",
            on_change=_sync_from_number,
            args=(field,),
        )
    st.caption(f"Ограничитель диапазона: от {min_val:g} до {max_val:g} {unit}")
    return float(st.session_state[f"form_{field}"])


def render_predict_page(service: ModelService) -> None:
    """Отрисовывает раздел прогнозирования стоимости автомобиля."""
    _init_form_state()
    metrics = service.get_metrics_summary()

    st.header("Прогнозирование цены автомобиля")
    st.caption("Все параметры защищены ограничителями допустимых диапазонов; стоимость рассчитывается в рублях (₽).")

    col_form, col_res = st.columns([1.08, 1.12], gap="large")

    with col_form:
        with st.container(border=True):
            st.subheader("Параметры автомобиля")
            model_name = st.selectbox(
                "Модель машинного обучения (версия и качество на тесте)",
                MODEL_NAMES,
                format_func=lambda m: format_model_with_quality(m, metrics),
                key="form_model",
            )

            c1, c2 = st.columns(2)
            with c1:
                brand = st.selectbox("Марка", ALLOWED_BRANDS, format_func=str.capitalize, key="form_brand")
                fuel = st.selectbox(
                    "Тип топлива",
                    ALLOWED_FUELS,
                    format_func=lambda x: FUEL_LABELS.get(x, x),
                    key="form_fueltype",
                )
                drive = st.selectbox(
                    "Тип привода",
                    ALLOWED_DRIVES,
                    format_func=lambda x: DRIVE_LABELS.get(x, x),
                    key="form_drivewheel",
                )
            with c2:
                carbody = st.selectbox(
                    "Тип кузова",
                    ALLOWED_BODIES,
                    format_func=lambda x: BODY_LABELS.get(x, x),
                    key="form_carbody",
                )
                aspiration = st.selectbox(
                    "Система наддува",
                    ALLOWED_ASPIRATIONS,
                    format_func=lambda x: ASPIRATION_LABELS.get(x, x),
                    key="form_aspiration",
                )

            hp = _bounded_numeric_input("horsepower", "Мощность двигателя", "л.с.")
            eng = _bounded_numeric_input("enginesize", "Объём двигателя", "куб. дюймы (cu in)")
            weight = _bounded_numeric_input("curbweight", "Снаряжённая масса", "фунты (lbs)")
            city_mpg = _bounded_numeric_input("citympg", "Расход топлива в городе", "миль/галлон (MPG)")
            hwy_mpg = _bounded_numeric_input("highwaympg", "Расход топлива на трассе", "миль/галлон (MPG)")

            b_save, b_reset = st.columns(2, gap="small")
            with b_save:
                save_clicked = st.button(
                    "Сохранить расчёт в историю",
                    type="primary",
                    use_container_width=True,
                )
            with b_reset:
                st.button(
                    "Сбросить параметры (Reset)",
                    on_click=reset_form_state,
                    use_container_width=True,
                )

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
    prob_info = describe_price_probability(res.price_probability, res.price_rub)
    model_label = format_model_with_quality(res.model_key, metrics)

    if save_clicked:
        rec_id = log_prediction("web_user", res.price_usd, res.price_rub, model_label, features, "Streamlit_Web")
        st.toast(f"Расчёт сохранён в локальную базу SQLite (ID: {rec_id})")

    with col_res:
        with st.container(border=True):
            st.subheader("Результат оценки")
            if res.clamped_warnings:
                st.warning("Сработал ограничитель входных данных:\n- " + "\n- ".join(res.clamped_warnings))

            m1, m2 = st.columns(2)
            m1.metric("Прогнозная цена (₽)", format_rub(res.price_rub))
            m2.metric(
                "Вероятность цены (±15%)",
                f"{res.price_probability:.1f}%",
                delta=res.probability_level,
                delta_color="off",
                help=prob_info["subject"],
            )

            st.caption(f"Сегмент: **{res.market_category}** · {res.comparison_to_average}")
            st.progress(
                min(1.0, max(0.0, res.market_percentile / 100.0)),
                text=f"Дороже {res.market_percentile:.1f}% автомобилей на рынке",
            )

            st.markdown(
                f"- **95% доверительный интервал (₽):** `{format_rub(res.ci_lower_rub)}` — `{format_rub(res.ci_upper_rub)}`\n"
                f"- **Выбранная модель:** {model_label}"
            )

            st.info(
                f"**Расшифровка вероятности цены**\n\n"
                f"- **Предмет:** {prob_info['subject']}.\n"
                f"- **Коридор ±15% для текущего прогноза:** от **{format_rub(res.probability_band_low_rub)}** "
                f"до **{format_rub(res.probability_band_high_rub)}**.\n"
                f"- **Оценка надёжности:** **{res.probability_level}**.\n"
                f"- **Допустимый диапазон шкалы:** {prob_info['valid_range']} "
                f"(80–99% — высокая надёжность, 60–79% — средняя, 5–59% — низкая)."
            )

        with st.container(border=True):
            st.subheader("Сравнение всех моделей (версия, качество и вероятность)")
            all_preds = service.predict_all_models(features)
            rows = [
                {
                    "Модель (версия и качество)": format_model_with_quality(p.model_key, metrics),
                    "Прогноз (₽)": format_rub(p.price_rub),
                    "Вероятность (±15%)": f"{p.price_probability:.1f}%",
                    "Уровень": p.probability_level.split(" (")[0],
                    "95% интервал (₽)": f"{format_rub(p.ci_lower_rub)} – {format_rub(p.ci_upper_rub)}",
                }
                for p in all_preds
            ]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
