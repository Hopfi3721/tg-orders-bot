"""Пользовательские сценарии: меню, форма заявки через FSM, список своих заявок."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app import keyboards as kb
from app import texts
from app.config import Config
from app.db import OrderStore
from app.notify import notify_admins
from app.states import OrderForm

logger = logging.getLogger(__name__)

router = Router(name="user")


@router.message(CommandStart())
async def start(message: Message, state: FSMContext) -> None:
    await state.clear()
    name = message.from_user.first_name if message.from_user else "друг"
    await message.answer(texts.WELCOME.format(name=name), reply_markup=kb.main_menu())


@router.message(Command("cancel"))
@router.message(F.text.lower() == "отмена")
async def cancel(message: Message, state: FSMContext) -> None:
    current = await state.get_state()
    await state.clear()
    if current is None:
        await message.answer("Нечего отменять.", reply_markup=kb.main_menu())
        return
    await message.answer(texts.CANCELLED, reply_markup=kb.main_menu())


@router.message(F.text == kb.BTN_CONTACT)
async def contact(message: Message, config: Config) -> None:
    await message.answer(
        texts.CONTACT.format(username=config.contact_username), reply_markup=kb.main_menu()
    )


@router.message(F.text == kb.BTN_MY_ORDERS)
async def my_orders(message: Message, store: OrderStore) -> None:
    orders = await store.list_by_user(message.from_user.id)
    if not orders:
        await message.answer(texts.NO_ORDERS, reply_markup=kb.main_menu())
        return

    for order in orders:
        await message.answer(
            texts.order_card(
                order.id,
                order.name,
                order.service,
                order.description,
                order.phone,
                order.status_label,
                order.created_at,
            )
        )


@router.message(F.text == kb.BTN_NEW_ORDER)
@router.message(Command("new"))
async def new_order(message: Message, state: FSMContext, store: OrderStore, config: Config) -> None:
    recent = await store.count_recent_by_user(
        message.from_user.id, config.throttle_window_seconds
    )
    if recent >= config.throttle_limit:
        minutes = max(1, config.throttle_window_seconds // 60)
        await message.answer(
            texts.THROTTLE_TEMPLATE.format(minutes=minutes), reply_markup=kb.main_menu()
        )
        return

    await state.clear()
    await state.set_state(OrderForm.name)
    await message.answer(texts.ASK_NAME, reply_markup=kb.cancel_menu())


@router.message(OrderForm.name)
async def process_name(message: Message, state: FSMContext) -> None:
    name = texts.normalize_name(message.text or "")
    if name is None:
        await message.answer("Имя должно быть от 2 до 80 символов. Попробуйте ещё раз.")
        return

    await state.update_data(name=name)
    await state.set_state(OrderForm.service)
    await message.answer(texts.ASK_SERVICE, reply_markup=kb.services_menu())


@router.callback_query(OrderForm.service, F.data.startswith("service:"))
async def process_service(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.data is None or callback.message is None:
        await callback.answer()
        return

    try:
        index = int(callback.data.split(":", 1)[1])
        service = kb.SERVICES[index]
    except (ValueError, IndexError):
        await callback.answer("Не понял выбор, попробуйте ещё раз", show_alert=True)
        return

    await state.update_data(service=service)
    await state.set_state(OrderForm.description)
    await callback.message.edit_text(f"Услуга: {service}")
    await callback.message.answer(texts.ASK_DESCRIPTION, reply_markup=kb.cancel_menu())
    await callback.answer()


@router.message(OrderForm.service)
async def service_fallback(message: Message) -> None:
    await message.answer(
        "Выберите услугу кнопкой выше — или нажмите «Отмена».",
        reply_markup=kb.services_menu(),
    )


@router.message(OrderForm.description)
async def process_description(message: Message, state: FSMContext) -> None:
    description = texts.normalize_description(message.text or "")
    if description is None:
        await message.answer("Описание должно быть от 10 до 1200 символов. Попробуйте ещё раз.")
        return

    await state.update_data(description=description)
    await state.set_state(OrderForm.phone)
    await message.answer(texts.ASK_PHONE, reply_markup=kb.cancel_menu())


@router.message(OrderForm.phone, F.contact)
async def process_contact_phone(message: Message, state: FSMContext) -> None:
    phone = texts.normalize_phone(message.contact.phone_number if message.contact else "")
    if phone is None:
        await message.answer("Не удалось разобрать номер. Введите его текстом.")
        return

    await state.update_data(phone=phone)
    await _ask_confirmation(message, state)


@router.message(OrderForm.phone)
async def process_phone(message: Message, state: FSMContext) -> None:
    phone = texts.normalize_phone(message.text or "")
    if phone is None:
        await message.answer("Нужен номер из 10–15 цифр, например +79991234567.")
        return

    await state.update_data(phone=phone)
    await _ask_confirmation(message, state)


async def _ask_confirmation(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await state.set_state(OrderForm.confirm)
    await message.answer(
        texts.CONFIRM_TEMPLATE.format(
            name=data["name"],
            service=data["service"],
            description=data["description"],
            phone=data["phone"],
        ),
        reply_markup=kb.confirm_menu(),
    )


@router.callback_query(OrderForm.confirm, F.data == "confirm:restart")
async def restart_form(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message is None:
        await callback.answer()
        return
    await state.clear()
    await state.set_state(OrderForm.name)
    await callback.message.edit_text("Заполним заново.")
    await callback.message.answer(texts.ASK_NAME, reply_markup=kb.cancel_menu())
    await callback.answer()


@router.callback_query(OrderForm.confirm, F.data == "confirm:cancel")
async def cancel_form(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message is None:
        await callback.answer()
        return
    await state.clear()
    await callback.message.edit_text(texts.CANCELLED)
    await callback.message.answer("Главное меню", reply_markup=kb.main_menu())
    await callback.answer()


@router.callback_query(OrderForm.confirm, F.data == "confirm:send")
async def send_order(
    callback: CallbackQuery, state: FSMContext, store: OrderStore, config: Config
) -> None:
    if callback.message is None or callback.from_user is None:
        await callback.answer()
        return

    data = await state.get_data()
    order_id = await store.create(
        user_id=callback.from_user.id,
        username=callback.from_user.username,
        name=data["name"],
        service=data["service"],
        description=data["description"],
        phone=data["phone"],
    )
    await state.clear()

    order = await store.get(order_id)
    if order is not None:
        await notify_admins(
            callback.message.bot,
            config.admin_ids,
            "Новая заявка\n\n"
            + texts.order_card(
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

    await callback.message.edit_text(texts.SENT_TEMPLATE.format(order_id=order_id))
    await callback.message.answer("Главное меню", reply_markup=kb.main_menu())
    await callback.answer("Заявка отправлена")


@router.message()
async def fallback(message: Message, state: FSMContext) -> None:
    if await state.get_state() is not None:
        await message.answer("Похоже, кнопка не та. Нажмите «Отмена», чтобы выйти.")
        return
    await message.answer("Выберите действие в меню ниже.", reply_markup=kb.main_menu())
