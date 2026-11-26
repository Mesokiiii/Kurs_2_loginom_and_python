"""Раздел готовых пресетов автомобилей с отображением цены в рублях и вероятности."""

import streamlit as st

from src.config import (
    ASPIRATION_LABELS,
    BODY_LABELS,
    CAR_PRESETS,
    DRIVE_LABELS,
    FUEL_LABELS,
    MODEL_NAMES,
    format_model_with_quality,
    format_rub,
)
from src.models.service import ModelService
from src.web.predict_page import apply_preset_to_state


def render_presets_page(service: ModelService) -> None:
    """Отрисовывает карточки типовых автомобилей с прогнозной ценой в рублях и вероятностью."""
    metrics = service.get_metrics_summary()

    st.header("Пресеты автомобилей")
    st.caption("Готовые конфигурации с мгновенным расчётом стоимости в рублях (₽) и вероятности попадания цены в коридор ±15%.")

    selected_model = st.selectbox(
        "Модель для расчёта пресетов (версия и качество на тесте)",
        MODEL_NAMES,
        index=0,
        format_func=lambda m: format_model_with_quality(m, metrics),
    )

    items = list(CAR_PRESETS.items())
    for row_start in range(0, len(items), 2):
        cols = st.columns(2, gap="medium")
        for idx, col in enumerate(cols):
            pos = row_start + idx
            if pos >= len(items):
                break
            name, data = items[pos]
            res = service.predict(data, model_selection=selected_model)

            body_ru = BODY_LABELS.get(data["carbody"], data["carbody"])
            fuel_ru = FUEL_LABELS.get(data["fueltype"], data["fueltype"])
            asp_ru = ASPIRATION_LABELS.get(data["aspiration"], data["aspiration"])
            drive_ru = DRIVE_LABELS.get(data["drivewheel"], data["drivewheel"])

            with col:
                with st.container(border=True):
                    st.subheader(name)
                    st.caption(data.get("description", ""))

                    m1, m2 = st.columns(2)
                    m1.metric("Прогноз цены (₽)", format_rub(res.price_rub), res.market_category, delta_color="off")
                    m2.metric(
                        "Вероятность (±15%)",
                        f"{res.price_probability:.1f}%",
                        res.probability_level,
                        delta_color="off",
                    )

                    st.markdown(
                        f"- **Марка / кузов:** {data['brand'].capitalize()} ({body_ru})\n"
                        f"- **Привод:** {drive_ru}\n"
                        f"- **Двигатель:** {data['horsepower']:.0f} л.с., {data['enginesize']:.0f} куб. дюймов (cu in), {fuel_ru} ({asp_ru})\n"
                        f"- **Масса и расход:** {data['curbweight']:.0f} фунтов (lbs) · {data['citympg']:.0f}/{data['highwaympg']:.0f} миль/галлон (MPG)\n"
                        f"- **Коридор ±15%:** `{format_rub(res.probability_band_low_rub)}` — `{format_rub(res.probability_band_high_rub)}`\n"
                        f"- **95% доверительный интервал:** `{format_rub(res.ci_lower_rub)}` — `{format_rub(res.ci_upper_rub)}`"
                    )

                    st.button(
                        "Открыть в калькуляторе",
                        key=f"preset_btn_{pos}",
                        on_click=apply_preset_to_state,
                        args=(data,),
                        use_container_width=True,
                    )
