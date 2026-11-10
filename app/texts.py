"""Тексты и валидация ввода — отдельно от хендлеров, чтобы их можно было тестировать."""

from __future__ import annotations

import re

MAX_NAME = 80
MAX_DESCRIPTION = 1200

WELCOME = (
    "Здравствуйте, {name}!\n\n"
    "Это бот приёма заявок. Оставьте заявку — я передам её исполнителю, "
    "а здесь же можно следить за статусом."
)

ASK_NAME = "Как к вам обращаться?"
ASK_SERVICE = "Что нужно сделать?"
ASK_DESCRIPTION = "Опишите задачу: что есть сейчас и какой результат нужен."
ASK_PHONE = (
    "Оставьте телефон для связи в формате +7XXXXXXXXXX или 8XXXXXXXXXX.\n"
    "Можно нажать «Отправить контакт» ниже."
)
CONFIRM_TEMPLATE = (
    "Проверьте заявку:\n\n"
    "Имя: {name}\n"
    "Услуга: {service}\n"
    "Задача: {description}\n"
    "Телефон: {phone}\n\n"
    "Всё верно?"
)

SENT_TEMPLATE = "Заявка №{order_id} принята. Я напишу, когда изменится статус."
THROTTLE_TEMPLATE = (
    "Слишком много заявок подряд. Попробуйте снова через {minutes} мин."
)
CANCELLED = "Хорошо, заявка отменена. Возвращайтесь, когда будете готовы."
NO_ORDERS = "У вас пока нет заявок."
CONTACT = (
    "Связаться с исполнителем: @{username}\n"
    "Или просто оставьте заявку — я отвечу здесь."
)


def normalize_name(raw: str) -> str | None:
    name = " ".join(raw.split())
    if len(name) < 2 or len(name) > MAX_NAME:
        return None
    return name


def normalize_description(raw: str) -> str | None:
    text = raw.strip()
    if len(text) < 10 or len(text) > MAX_DESCRIPTION:
        return None
    return text


_PHONE_RE = re.compile(r"^\+?\d{10,15}$")


def normalize_phone(raw: str) -> str | None:
    digits = re.sub(r"[\s\-()]", "", raw.strip())
    if not _PHONE_RE.match(digits):
        return None
    if digits.startswith("8") and len(digits) == 11:
        digits = "+7" + digits[1:]
    return digits


def order_card(order_id: int, name: str, service: str, description: str, phone: str,
               status: str, created_at: str) -> str:
    return (
        f"Заявка №{order_id}\n"
        f"Дата: {created_at}\n"
        f"Имя: {name}\n"
        f"Услуга: {service}\n"
        f"Задача: {description}\n"
        f"Телефон: {phone}\n"
        f"Статус: {status}"
    )
