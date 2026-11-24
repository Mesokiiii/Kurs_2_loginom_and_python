"""Раздел готовых пресетов автомобилей с отображением цены и вероятности."""

import streamlit as st

from src.config import CAR_PRESETS, MODEL_NAMES
from src.models.service import ModelService
from src.web.predict_page import apply_preset_to_state


def render_presets_page(service: ModelService) -> None:
    """Отрисовывает карточки типовых автомобилей с прогнозной ценой и вероятностью."""
    st.header("Пресеты автомобилей")
    st.caption("Готовые конфигурации с мгновенным прогнозом стоимости и вероятности попадания в ±15%.")

    selected_model = st.selectbox("Модель для расчёта пресетов", MODEL_NAMES, index=0)

    items = list(CAR_PRESETS.items())
    for row_start in range(0, len(items), 2):
        cols = st.columns(2, gap="medium")
        for idx, col in enumerate(cols):
            pos = row_start + idx
            if pos >= len(items):
                break
            name, data = items[pos]
            res = service.predict(data, model_selection=selected_model)

            with col:
                with st.container(border=True):
                    st.subheader(name)
                    st.caption(data.get("description", ""))

                    m1, m2 = st.columns(2)
                    m1.metric("Прогноз цены", f"${res.price_usd:,.0f}", f"{res.price_rub:,.0f} ₽", delta_color="off")
                    m2.metric("Вероятность цены", f"{res.price_probability:.1f}%", res.market_category, delta_color="off")

                    st.markdown(
                        f"- **Марка / кузов:** {data['brand'].capitalize()} ({data['carbody']})\n"
                        f"- **Двигатель:** {data['horsepower']:.0f} л.с., {data['enginesize']:.0f} cu in, {data['fueltype']} ({data['aspiration']})\n"
                        f"- **Масса и расход:** {data['curbweight']:.0f} lbs · {data['citympg']:.0f}/{data['highwaympg']:.0f} MPG\n"
                        f"- **95% интервал:** `${res.ci_lower_usd:,.0f}` — `${res.ci_upper_usd:,.0f}`"
                    )

                    st.button(
                        "Открыть в калькуляторе",
                        key=f"preset_btn_{pos}",
                        on_click=apply_preset_to_state,
                        args=(data,),
                        use_container_width=True,
                    )
