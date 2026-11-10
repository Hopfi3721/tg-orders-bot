"""Роутеры бота."""

from aiogram import Router

from app.handlers import admin, user


def build_router() -> Router:
    root = Router(name="root")
    root.include_router(admin.router)
    root.include_router(user.router)
    return root
