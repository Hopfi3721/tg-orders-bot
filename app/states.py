"""Состояния FSM для формы заявки."""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class OrderForm(StatesGroup):
    name = State()
    service = State()
    description = State()
    phone = State()
    confirm = State()
