"""Запуск Telegram-бота на aiogram 3.

Пример запуска:
    set BOT_TOKEN=123456:ABC...
    python run_bot.py
"""

import asyncio
import os
from pathlib import Path

from src.bot.app import start_bot


def _load_token() -> str:
    token = os.getenv("BOT_TOKEN", "").strip()
    if token:
        return token

    env_path = Path(__file__).resolve().parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("BOT_TOKEN="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def main() -> None:
    token = _load_token()
    if not token:
        print("Укажите токен бота в переменной окружения BOT_TOKEN или в файле .env (BOT_TOKEN=...)")
        return
    asyncio.run(start_bot(token))


if __name__ == "__main__":
    main()
