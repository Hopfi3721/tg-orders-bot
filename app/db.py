"""Слой хранения заявок: SQLite через stdlib sqlite3, без блокировки event loop."""

from __future__ import annotations

import asyncio
import csv
import io
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

STATUSES: tuple[str, ...] = ("new", "in_progress", "done", "rejected")

STATUS_LABELS: dict[str, str] = {
    "new": "Новая",
    "in_progress": "В работе",
    "done": "Готово",
    "rejected": "Отклонена",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    username    TEXT,
    name        TEXT NOT NULL,
    service     TEXT NOT NULL,
    description TEXT NOT NULL,
    phone       TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'new',
    created_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_orders_user   ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_created ON orders(created_at);
"""


@dataclass(frozen=True)
class Order:
    id: int
    user_id: int
    username: str | None
    name: str
    service: str
    description: str
    phone: str
    status: str
    created_at: str

    @property
    def status_label(self) -> str:
        return STATUS_LABELS.get(self.status, self.status)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class OrderStore:
    """Минимальный async-репозиторий: один короткоживущий коннект на операцию."""

    def __init__(self, path: str) -> None:
        self._path = path

    # --- инфраструктура -----------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path, timeout=5)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    async def _call(self, func: Any, *args: Any) -> Any:
        return await asyncio.to_thread(func, *args)

    async def init(self) -> None:
        Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        await self._call(self._init_sync)

    def _init_sync(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    # --- запись -------------------------------------------------------------

    async def create(
        self,
        *,
        user_id: int,
        username: str | None,
        name: str,
        service: str,
        description: str,
        phone: str,
    ) -> int:
        return await self._call(
            self._create_sync, user_id, username, name, service, description, phone
        )

    def _create_sync(
        self,
        user_id: int,
        username: str | None,
        name: str,
        service: str,
        description: str,
        phone: str,
    ) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO orders
                    (user_id, username, name, service, description, phone, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'new', ?)
                """,
                (user_id, username, name, service, description, phone, _now()),
            )
            return int(cur.lastrowid)

    async def set_status(self, order_id: int, status: str) -> bool:
        if status not in STATUSES:
            raise ValueError(f"неизвестный статус: {status}")
        return await self._call(self._set_status_sync, order_id, status)

    def _set_status_sync(self, order_id: int, status: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE orders SET status = ? WHERE id = ?", (status, order_id)
            )
            return cur.rowcount > 0

    # --- чтение -------------------------------------------------------------

    async def get(self, order_id: int) -> Order | None:
        return await self._call(self._get_sync, order_id)

    def _get_sync(self, order_id: int) -> Order | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        return _row_to_order(row) if row else None

    async def list_recent(self, limit: int = 10, status: str | None = None) -> list[Order]:
        return await self._call(self._list_recent_sync, limit, status)

    def _list_recent_sync(self, limit: int, status: str | None) -> list[Order]:
        query = "SELECT * FROM orders"
        params: tuple[Any, ...] = ()
        if status:
            query += " WHERE status = ?"
            params = (status,)
        query += " ORDER BY id DESC LIMIT ?"
        with self._connect() as conn:
            rows = conn.execute(query, (*params, limit)).fetchall()
        return [_row_to_order(row) for row in rows]

    async def list_by_user(self, user_id: int, limit: int = 10) -> list[Order]:
        return await self._call(self._list_by_user_sync, user_id, limit)

    def _list_by_user_sync(self, user_id: int, limit: int) -> list[Order]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                (user_id, limit),
            ).fetchall()
        return [_row_to_order(row) for row in rows]

    async def counts(self) -> dict[str, int]:
        return await self._call(self._counts_sync)

    def _counts_sync(self) -> dict[str, int]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT status, COUNT(*) AS n FROM orders GROUP BY status"
            ).fetchall()
        result = {status: 0 for status in STATUSES}
        for row in rows:
            result[str(row["status"])] = int(row["n"])
        return result

    async def count_recent_by_user(self, user_id: int, window_seconds: int) -> int:
        return await self._call(self._count_recent_sync, user_id, window_seconds)

    def _count_recent_sync(self, user_id: int, window_seconds: int) -> int:
        border = (
            datetime.now(timezone.utc) - timedelta(seconds=window_seconds)
        ).isoformat(timespec="seconds")
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM orders WHERE user_id = ? AND created_at >= ?",
                (user_id, border),
            ).fetchone()
        return int(row["n"])

    # --- выгрузка -----------------------------------------------------------

    async def export_csv(self) -> bytes:
        return await self._call(self._export_csv_sync)

    def _export_csv_sync(self) -> bytes:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM orders ORDER BY id").fetchall()

        buffer = io.StringIO()
        writer = csv.writer(buffer, delimiter=";", lineterminator="\r\n")
        writer.writerow(
            ["ID", "Дата", "Пользователь", "Имя", "Услуга", "Описание", "Телефон", "Статус"]
        )
        for row in rows:
            order = _row_to_order(row)
            writer.writerow(
                [
                    order.id,
                    order.created_at,
                    f"@{order.username}" if order.username else order.user_id,
                    order.name,
                    order.service,
                    order.description.replace("\n", " "),
                    order.phone,
                    order.status_label,
                ]
            )

        # BOM нужен, чтобы Excel на Windows не ломал кириллицу.
        return ("\ufeff" + buffer.getvalue()).encode("utf-8")


def _row_to_order(row: sqlite3.Row) -> Order:
    return Order(
        id=int(row["id"]),
        user_id=int(row["user_id"]),
        username=row["username"],
        name=str(row["name"]),
        service=str(row["service"]),
        description=str(row["description"]),
        phone=str(row["phone"]),
        status=str(row["status"]),
        created_at=str(row["created_at"]),
    )
