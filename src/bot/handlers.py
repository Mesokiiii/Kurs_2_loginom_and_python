"""Обработчики команд и сообщений Telegram-бота на aiogram 3."""

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.config import CAR_PRESETS, FEATURE_DEFAULTS, MODEL_NAMES
from src.models.service import ModelService
from src.storage.repository import get_overall_stats, get_user_history, log_prediction
from src.bot.formatting import format_history, format_prediction, format_presets_overview
from src.bot.keyboards import (
    BTN_CANCEL,
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


def build_router(service: ModelService) -> Router:
    """Создаёт роутер с обработчиками бота."""
    router = Router()
    preset_items = list(CAR_PRESETS.items())

    @router.message(CommandStart())
    @router.message(Command("help"))
    async def cmd_start(message: Message, state: FSMContext) -> None:
        await state.clear()
        await message.answer(
            "<b>CarPrice Predictor ML</b>\n\n"
            "Бот оценивает стоимость автомобиля по характеристикам и показывает "
            "вероятность попадания цены в диапазон ±15%.\n\n"
            "Выберите раздел в меню ниже:",
            reply_markup=main_menu_kb(),
        )

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
        res = service.predict(data, model_selection=MODEL_NAMES[0])
        user = callback.from_user
        log_prediction(user.id, res.price_usd, res.price_rub, res.model_name, data, user.username)

        await callback.message.answer(format_prediction(res, data, title=name))
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
        await state.update_data(carbody=body)
        await state.set_state(PredictForm.horsepower)
        await callback.message.answer(
            f"Кузов: <b>{body.capitalize()}</b>\n"
            "Шаг 3/6. Введите мощность двигателя в л.с. (от 48 до 288, например 110):"
        )
        await callback.answer()

    @router.message(PredictForm.horsepower)
    async def step_horsepower(message: Message, state: FSMContext) -> None:
        hp = _parse_float(message.text or "", 48.0, 288.0)
        if hp is None:
            await message.answer("Введите число от 48 до 288.")
            return
        await state.update_data(horsepower=hp)
        await state.set_state(PredictForm.enginesize)
        await message.answer("Шаг 4/6. Введите объем двигателя в cu in (от 61 до 326, например 130):")

    @router.message(PredictForm.enginesize)
    async def step_enginesize(message: Message, state: FSMContext) -> None:
        eng = _parse_float(message.text or "", 61.0, 326.0)
        if eng is None:
            await message.answer("Введите число от 61 до 326.")
            return
        await state.update_data(enginesize=eng)
        await state.set_state(PredictForm.curbweight)
        await message.answer("Шаг 5/6. Введите массу автомобиля в lbs (от 1488 до 4066, например 2500):")

    @router.message(PredictForm.curbweight)
    async def step_curbweight(message: Message, state: FSMContext) -> None:
        weight = _parse_float(message.text or "", 1488.0, 4066.0)
        if weight is None:
            await message.answer("Введите число от 1488 до 4066.")
            return
        await state.update_data(curbweight=weight)
        await state.set_state(PredictForm.model)
        await message.answer("Шаг 6/6. Выберите модель ML:", reply_markup=models_kb())

    @router.callback_query(PredictForm.model, F.data.startswith("model:"))
    async def step_model(callback: CallbackQuery, state: FSMContext) -> None:
        idx = int(callback.data.split(":")[1])
        model_name = MODEL_NAMES[idx] if 0 <= idx < len(MODEL_NAMES) else MODEL_NAMES[0]

        form_data = await state.get_data()
        features = dict(FEATURE_DEFAULTS)
        features.update(form_data)

        res = service.predict(features, model_selection=model_name)
        user = callback.from_user
        log_prediction(user.id, res.price_usd, res.price_rub, res.model_name, features, user.username)

        await state.clear()
        await callback.message.answer(
            format_prediction(res, features),
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
        await message.answer(
            "<b>Статистика базы расчётов</b>\n\n"
            f"Всего расчётов: <b>{st['total_queries']}</b>\n"
            f"Пользователей: <b>{st['unique_users']}</b>\n"
            f"Средняя цена: <b>${st['avg_predicted_price_usd']:,.0f}</b>\n"
            f"Популярная марка: <b>{str(st['top_brand']).capitalize()}</b>\n"
            f"Популярная модель: <b>{st['top_model']}</b>"
        )

    return router
