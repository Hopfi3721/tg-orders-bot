"""Тесты слоя хранения: работают без сети и без Telegram."""

from __future__ import annotations

import asyncio

from app.db import OrderStore


def _run(coro):
    return asyncio.run(coro)


def make_store(tmp_path) -> OrderStore:
    store = OrderStore(str(tmp_path / "test.db"))
    _run(store.init())
    return store


def test_create_and_get(tmp_path):
    store = make_store(tmp_path)

    order_id = _run(
        store.create(
            user_id=42,
            username="tester",
            name="Иван",
            service="Telegram-бот",
            description="Нужен бот для заявок",
            phone="+79991234567",
        )
    )

    order = _run(store.get(order_id))
    assert order is not None
    assert order.id == order_id
    assert order.name == "Иван"
    assert order.status == "new"
    assert order.status_label == "Новая"


def test_get_missing_returns_none(tmp_path):
    store = make_store(tmp_path)
    assert _run(store.get(999)) is None


def test_status_transition(tmp_path):
    store = make_store(tmp_path)
    order_id = _run(
        store.create(
            user_id=1,
            username=None,
            name="Пётр",
            service="Парсер",
            description="Собрать каталог товаров",
            phone="+79990000000",
        )
    )

    assert _run(store.set_status(order_id, "in_progress")) is True
    order = _run(store.get(order_id))
    assert order is not None and order.status == "in_progress"

    assert _run(store.set_status(999, "done")) is False


def test_counts_and_lists(tmp_path):
    store = make_store(tmp_path)
    for index in range(3):
        _run(
            store.create(
                user_id=index,
                username=f"u{index}",
                name="Клиент",
                service="Другое",
                description=f"Задача номер {index}",
                phone="+79991112233",
            )
        )

    counts = _run(store.counts())
    assert counts["new"] == 3
    assert counts["done"] == 0

    recent = _run(store.list_recent(limit=2))
    assert len(recent) == 2
    assert recent[0].id > recent[1].id

    by_user = _run(store.list_by_user(1))
    assert len(by_user) == 1


def test_throttle_counter(tmp_path):
    store = make_store(tmp_path)
    _run(
        store.create(
            user_id=7,
            username=None,
            name="Анна",
            service="Другое",
            description="Проверка антифлуда",
            phone="+79995554433",
        )
    )

    assert _run(store.count_recent_by_user(7, 3600)) == 1
    assert _run(store.count_recent_by_user(8, 3600)) == 0


def test_csv_export_is_excel_friendly(tmp_path):
    store = make_store(tmp_path)
    _run(
        store.create(
            user_id=5,
            username="client",
            name="Олег",
            service="Сайт",
            description="Лендинг с формой",
            phone="+79990001122",
        )
    )

    payload = _run(store.export_csv())

    assert payload.startswith(b"\xef\xbb\xbf"), "нужен BOM для Excel"
    text = payload.decode("utf-8-sig")
    assert text.splitlines()[0].startswith("ID;Дата;")
    assert "@client" in text
    assert "Олег" in text
