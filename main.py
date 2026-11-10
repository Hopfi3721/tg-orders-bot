"""Точка входа: конфиг, хранилище, роутеры, polling."""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import load_config
from app.db import OrderStore
from app.handlers import build_router

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )


async def run() -> None:
    config = load_config()

    store = OrderStore(config.db_path)
    await store.init()
    logger.info("база готова: %s", config.db_path)

    bot = Bot(token=config.bot_token)
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.include_router(build_router())

    me = await bot.get_me()
    logger.info("запущен @%s (id=%s)", me.username, me.id)

    # store и config попадают в хендлеры как обычные аргументы
    await dispatcher.start_polling(bot, store=store, config=config)


def main() -> None:
    setup_logging()
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info("остановлено пользователем")


if __name__ == "__main__":
    main()
