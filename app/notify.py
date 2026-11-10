"""Уведомления администраторов и пользователей: ошибки Telegram не должны ломать сценарий."""

from __future__ import annotations

import logging
from typing import Iterable

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import InlineKeyboardMarkup

logger = logging.getLogger(__name__)


async def safe_send(
    bot: Bot,
    chat_id: int,
    text: str,
    *,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> bool:
    """Отправить сообщение, проглотив ожидаемые ошибки Telegram."""
    try:
        await bot.send_message(chat_id, text, reply_markup=reply_markup)
    except TelegramAPIError as exc:
        logger.warning("не удалось отправить сообщение %s: %s", chat_id, exc)
        return False
    return True


async def notify_admins(
    bot: Bot,
    admin_ids: Iterable[int],
    text: str,
    *,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> int:
    sent = 0
    for admin_id in admin_ids:
        if await safe_send(bot, admin_id, text, reply_markup=reply_markup):
            sent += 1
    return sent
