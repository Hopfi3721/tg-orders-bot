"""Клавиатуры бота."""

from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

BTN_NEW_ORDER = "Оставить заявку"
BTN_MY_ORDERS = "Мои заявки"
BTN_CONTACT = "Связаться"

SERVICES: tuple[str, ...] = (
    "Telegram-бот",
    "Парсер / выгрузка",
    "Сайт или лендинг",
    "Автоматизация",
    "Другое",
)


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_NEW_ORDER)],
            [KeyboardButton(text=BTN_MY_ORDERS), KeyboardButton(text=BTN_CONTACT)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие",
    )


def services_menu() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=service, callback_data=f"service:{index}")]
        for index, service in enumerate(SERVICES)
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def cancel_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Отмена")]],
        resize_keyboard=True,
    )


def confirm_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Отправить", callback_data="confirm:send"),
                InlineKeyboardButton(text="Заполнить заново", callback_data="confirm:restart"),
            ],
            [InlineKeyboardButton(text="Отмена", callback_data="confirm:cancel")],
        ]
    )


def order_actions(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="В работу", callback_data=f"admin:status:{order_id}:in_progress"
                ),
                InlineKeyboardButton(
                    text="Готово", callback_data=f"admin:status:{order_id}:done"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Отклонить", callback_data=f"admin:status:{order_id}:rejected"
                )
            ],
        ]
    )


def admin_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Последние 10 заявок", callback_data="admin:list")],
            [InlineKeyboardButton(text="Выгрузить CSV", callback_data="admin:csv")],
        ]
    )


def remove_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()
