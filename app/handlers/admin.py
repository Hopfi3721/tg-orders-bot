"""Админ-панель: сводка, последние заявки, смена статуса, выгрузка CSV."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from app import keyboards as kb
from app import texts
from app.config import Config
from app.db import STATUS_LABELS, STATUSES, OrderStore
from app.notify import safe_send

logger = logging.getLogger(__name__)

router = Router(name="admin")

STATUS_MESSAGES: dict[str, str] = {
    "in_progress": "взята в работу",
    "done": "выполнена",
    "rejected": "отклонена",
}


def _summary(counts: dict[str, int]) -> str:
    lines = ["Сводка по заявкам", ""]
    for status in STATUSES:
        lines.append(f"{STATUS_LABELS[status]}: {counts.get(status, 0)}")
    lines.append("")
    lines.append(f"Всего: {sum(counts.values())}")
    return "\n".join(lines)


@router.message(Command("admin"))
async def admin_panel(message: Message, store: OrderStore, config: Config) -> None:
    if not config.is_admin(message.from_user.id):
        return

    counts = await store.counts()
    await message.answer(_summary(counts), reply_markup=kb.admin_menu())


@router.callback_query(F.data == "admin:list")
async def admin_list(callback: CallbackQuery, store: OrderStore, config: Config) -> None:
    if not config.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    if callback.message is None:
        await callback.answer()
        return

    orders = await store.list_recent(limit=10)
    if not orders:
        await callback.message.answer("Заявок пока нет.")
        await callback.answer()
        return

    for order in orders:
        await callback.message.answer(
            texts.order_card(
                order.id,
                order.name,
                order.service,
                order.description,
                order.phone,
                order.status_label,
                order.created_at,
            ),
            reply_markup=kb.order_actions(order.id),
        )
    await callback.answer()


@router.callback_query(F.data == "admin:csv")
async def admin_csv(callback: CallbackQuery, store: OrderStore, config: Config) -> None:
    if not config.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    if callback.message is None:
        await callback.answer()
        return

    payload = await store.export_csv()
    await callback.message.answer_document(
        BufferedInputFile(payload, filename="orders.csv"),
        caption="Выгрузка всех заявок (Excel откроет сразу)",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:status:"))
async def admin_set_status(
    callback: CallbackQuery, store: OrderStore, config: Config
) -> None:
    if not config.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    parts = (callback.data or "").split(":")
    if len(parts) != 4:
        await callback.answer("Некорректная кнопка", show_alert=True)
        return

    try:
        order_id = int(parts[2])
    except ValueError:
        await callback.answer("Некорректный номер заявки", show_alert=True)
        return

    status = parts[3]
    if status not in STATUSES:
        await callback.answer("Неизвестный статус", show_alert=True)
        return

    if not await store.set_status(order_id, status):
        await callback.answer("Заявка не найдена", show_alert=True)
        return

    order = await store.get(order_id)
    if order is not None:
        await safe_send(
            callback.bot,
            order.user_id,
            f"Статус заявки №{order.id} изменён: {STATUS_MESSAGES.get(status, status)}.",
        )

    if callback.message is not None:
        await callback.message.edit_text(
            f"Заявка №{order_id}: статус «{STATUS_LABELS[status]}»"
        )

    await callback.answer("Готово")
