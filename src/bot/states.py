"""Состояния FSM для пошагового расчёта стоимости автомобиля."""

from aiogram.fsm.state import State, StatesGroup


class PredictForm(StatesGroup):
    brand = State()
    carbody = State()
    horsepower = State()
    enginesize = State()
    curbweight = State()
    model = State()
