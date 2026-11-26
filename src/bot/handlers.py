"""Обработчики команд и сообщений Telegram-бота на aiogram 3."""

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.config import (
    BODY_LABELS,
    CAR_PRESETS,
    FEATURE_DEFAULTS,
    FEATURE_RANGES,
    MODEL_NAMES,
    MODEL_VERSION,
    USD_TO_RUB_RATE,
    format_model_with_quality,
    format_rub,
)
from src.models.service import ModelService
from src.storage.repository import get_overall_stats, get_user_history, log_prediction
from src.bot.formatting import format_history, format_prediction, format_presets_overview
from src.bot.keyboards import (
    BTN_CANCEL,
    BTN_HELP,
    BTN_HISTORY,
    BTN_PREDICT,
    BTN_PRESETS,
    BTN_STATS,
    bodies_kb,
    brands_kb,
    cancel_kb,
    main_menu_kb,
    models_kb,
    presets_kb,
)
from src.bot.states import PredictForm


def _parse_float(text: str, min_val: float, max_val: float) -> float | None:
    try:
        val = float(text.replace(",", ".").strip())
    except ValueError:
        return None
    if min_val <= val <= max_val:
        return val
    return None


def _build_help_text(service: ModelService) -> str:
    metrics = service.get_metrics_summary()
    hp_lo, hp_hi, _ = FEATURE_RANGES["horsepower"]
    eng_lo, eng_hi, _ = FEATURE_RANGES["enginesize"]
    w_lo, w_hi, _ = FEATURE_RANGES["curbweight"]
    models_lines = "\n".join(
        f"  • {format_model_with_quality(name, metrics)}" for name in MODEL_NAMES
    )
    return (
        f"<b>Справка — CarPrice Predictor ML (модели {MODEL_VERSION})</b>\n\n"
        "<b>Как пользоваться ботом:</b>\n"
        "1. «Пресеты авто» — мгновенный расчёт 4 типовых конфигураций.\n"
        "2. «Рассчитать авто» — пошаговый ввод марки, кузова, мощности, объёма, массы и модели.\n"
        "3. «История» и «Статистика» — просмотр расчётов из локальной базы SQLite.\n\n"
        "<b>Ограничители числовых параметров:</b>\n"
        f"• Мощность двигателя: <b>{hp_lo:g}–{hp_hi:g} л.с.</b>\n"
        f"• Объём двигателя: <b>{eng_lo:g}–{eng_hi:g} куб. дюймов (cu in)</b>\n"
        f"• Снаряжённая масса: <b>{w_lo:g}–{w_hi:g} фунтов (lbs)</b>\n\n"
        "<b>Вероятность цены (±15%):</b>\n"
        "Показывает вероятность попадания реальной рыночной цены в коридор ±15% от прогноза модели. "
        "Шкала ограничена диапазоном <b>5%–99%</b>:\n"
        "• <b>80–99%</b> — высокая надёжность;\n"
        "• <b>60–79%</b> — средняя надёжность;\n"
        "• <b>5–59%</b> — низкая надёжность.\n\n"
        "<b>Доступные модели (версия и качество на тесте):</b>\n"
        f"{models_lines}\n\n"
        "Все цены отображаются в рублях (₽)."
    )


def build_router(service: ModelService) -> Router:
    """Создаёт роутер с обработчиками бота."""
    router = Router()
    preset_items = list(CAR_PRESETS.items())

    @router.message(CommandStart())
    async def cmd_start(message: Message, state: FSMContext) -> None:
        await state.clear()
        await message.answer(
            f"<b>CarPrice Predictor ML (модели {MODEL_VERSION})</b>\n\n"
            "Бот оценивает рыночную стоимость автомобиля в рублях (₽), рассчитывает "
            "95% доверительный интервал и вероятность попадания цены в коридор ±15%.\n\n"
            "Выберите раздел в меню ниже или нажмите «Справка»:",
            reply_markup=main_menu_kb(),
        )

    @router.message(Command("help"))
    @router.message(F.text == BTN_HELP)
    async def cmd_help(message: Message, state: FSMContext) -> None:
        await state.clear()
        await message.answer(_build_help_text(service), reply_markup=main_menu_kb())

    @router.message(F.text == BTN_CANCEL)
    @router.message(Command("cancel"))
    async def cmd_cancel(message: Message, state: FSMContext) -> None:
        await state.clear()
        await message.answer("Действие отменено.", reply_markup=main_menu_kb())

    @router.message(F.text == BTN_PRESETS)
    @router.message(Command("presets"))
    async def show_presets(message: Message) -> None:
        text = format_presets_overview(service)
        await message.answer(text, reply_markup=presets_kb())

    @router.callback_query(F.data.startswith("preset:"))
    async def on_preset_click(callback: CallbackQuery) -> None:
        idx = int(callback.data.split(":")[1])
        if idx < 0 or idx >= len(preset_items):
            await callback.answer("Пресет не найден", show_alert=True)
            return

        name, data = preset_items[idx]
        metrics = service.get_metrics_summary()
        res = service.predict(data, model_selection=MODEL_NAMES[0])
        model_label = format_model_with_quality(res.model_key, metrics)
        user = callback.from_user
        log_prediction(user.id, res.price_usd, res.price_rub, model_label, data, user.username)

        await callback.message.answer(format_prediction(res, data, title=name, metrics=metrics))
        await callback.answer()

    @router.message(F.text == BTN_PREDICT)
    @router.message(Command("predict"))
    async def start_predict(message: Message, state: FSMContext) -> None:
        await state.clear()
        await state.set_state(PredictForm.brand)
        await message.answer("Шаг 1/6. Выберите марку автомобиля:", reply_markup=cancel_kb())
        await message.answer("Популярные марки:", reply_markup=brands_kb())

    @router.callback_query(PredictForm.brand, F.data.startswith("brand:"))
    async def step_brand(callback: CallbackQuery, state: FSMContext) -> None:
        brand = callback.data.split(":")[1]
        await state.update_data(brand=brand)
        await state.set_state(PredictForm.carbody)
        await callback.message.answer(
            f"Марка: <b>{brand.capitalize()}</b>\nШаг 2/6. Выберите тип кузова:",
            reply_markup=bodies_kb(),
        )
        await callback.answer()

    @router.callback_query(PredictForm.carbody, F.data.startswith("body:"))
    async def step_body(callback: CallbackQuery, state: FSMContext) -> None:
        body = callback.data.split(":")[1]
        body_ru = BODY_LABELS.get(body, body.capitalize())
        hp_lo, hp_hi, _ = FEATURE_RANGES["horsepower"]
        await state.update_data(carbody=body)
        await state.set_state(PredictForm.horsepower)
        await callback.message.answer(
            f"Кузов: <b>{body_ru}</b>\n"
            f"Шаг 3/6. Введите мощность двигателя в л.с. "
            f"(ограничитель: от {hp_lo:g} до {hp_hi:g}, например 110):"
        )
        await callback.answer()

    @router.message(PredictForm.horsepower)
    async def step_horsepower(message: Message, state: FSMContext) -> None:
        hp_lo, hp_hi, _ = FEATURE_RANGES["horsepower"]
        hp = _parse_float(message.text or "", hp_lo, hp_hi)
        if hp is None:
            await message.answer(
                f"Сработал ограничитель диапазона. Введите мощность двигателя от {hp_lo:g} до {hp_hi:g} л.с."
            )
            return
        eng_lo, eng_hi, _ = FEATURE_RANGES["enginesize"]
        await state.update_data(horsepower=hp)
        await state.set_state(PredictForm.enginesize)
        await message.answer(
            f"Шаг 4/6. Введите объём двигателя в куб. дюймах (cu in) "
            f"(ограничитель: от {eng_lo:g} до {eng_hi:g}, например 130):"
        )

    @router.message(PredictForm.enginesize)
    async def step_enginesize(message: Message, state: FSMContext) -> None:
        eng_lo, eng_hi, _ = FEATURE_RANGES["enginesize"]
        eng = _parse_float(message.text or "", eng_lo, eng_hi)
        if eng is None:
            await message.answer(
                f"Сработал ограничитель диапазона. Введите объём двигателя от {eng_lo:g} до {eng_hi:g} куб. дюймов."
            )
            return
        w_lo, w_hi, _ = FEATURE_RANGES["curbweight"]
        await state.update_data(enginesize=eng)
        await state.set_state(PredictForm.curbweight)
        await message.answer(
            f"Шаг 5/6. Введите снаряжённую массу автомобиля в фунтах (lbs) "
            f"(ограничитель: от {w_lo:g} до {w_hi:g}, например 2500):"
        )

    @router.message(PredictForm.curbweight)
    async def step_curbweight(message: Message, state: FSMContext) -> None:
        w_lo, w_hi, _ = FEATURE_RANGES["curbweight"]
        weight = _parse_float(message.text or "", w_lo, w_hi)
        if weight is None:
            await message.answer(
                f"Сработал ограничитель диапазона. Введите массу автомобиля от {w_lo:g} до {w_hi:g} фунтов."
            )
            return
        await state.update_data(curbweight=weight)
        await state.set_state(PredictForm.model)
        await message.answer(
            "Шаг 6/6. Выберите модель машинного обучения (в скобках указана точность R²):",
            reply_markup=models_kb(service.get_metrics_summary()),
        )

    @router.callback_query(PredictForm.model, F.data.startswith("model:"))
    async def step_model(callback: CallbackQuery, state: FSMContext) -> None:
        idx = int(callback.data.split(":")[1])
        model_name = MODEL_NAMES[idx] if 0 <= idx < len(MODEL_NAMES) else MODEL_NAMES[0]

        form_data = await state.get_data()
        features = dict(FEATURE_DEFAULTS)
        features.update(form_data)

        metrics = service.get_metrics_summary()
        res = service.predict(features, model_selection=model_name)
        model_label = format_model_with_quality(res.model_key, metrics)
        user = callback.from_user
        log_prediction(user.id, res.price_usd, res.price_rub, model_label, features, user.username)

        await state.clear()
        await callback.message.answer(
            format_prediction(res, features, metrics=metrics),
            reply_markup=main_menu_kb(),
        )
        await callback.answer()

    @router.message(F.text == BTN_HISTORY)
    @router.message(Command("history"))
    async def show_history(message: Message) -> None:
        records = get_user_history(message.from_user.id, limit=5)
        await message.answer(format_history(records))

    @router.message(F.text == BTN_STATS)
    @router.message(Command("stats"))
    async def show_stats(message: Message) -> None:
        st = get_overall_stats()
        avg_rub = st["avg_predicted_price_usd"] * USD_TO_RUB_RATE
        await message.answer(
            "<b>Статистика локальной базы SQLite</b>\n\n"
            f"Всего расчётов: <b>{st['total_queries']}</b>\n"
            f"Пользователей: <b>{st['unique_users']}</b>\n"
            f"Средняя прогнозная цена: <b>{format_rub(avg_rub)}</b>\n"
            f"Популярная марка: <b>{str(st['top_brand']).capitalize()}</b>\n"
            f"Популярная модель: <b>{st['top_model']}</b>"
        )

    return router
