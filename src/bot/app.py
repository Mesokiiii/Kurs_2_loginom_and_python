"""Сборка и запуск Telegram-бота на aiogram 3."""

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from src.bot.handlers import build_router
from src.models.service import ModelService


def create_dispatcher(service: ModelService | None = None) -> Dispatcher:
    """Создаёт диспетчер aiogram 3 с подключённым роутером."""
    svc = service or ModelService()
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(build_router(svc))
    return dp


async def start_bot(token: str) -> None:
    """Запускает long-polling Telegram-бота."""
    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = create_dispatcher()
    await dp.start_polling(bot)
