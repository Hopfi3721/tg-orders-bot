"""Настройки бота: читаются из окружения или из .env рядом с проектом."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_env_file(path: Path) -> None:
    """Подхватить KEY=VALUE из .env, не перетирая уже заданные переменные."""
    if not path.is_file():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


def _parse_admin_ids(raw: str) -> tuple[int, ...]:
    ids: list[int] = []
    for chunk in raw.replace(";", ",").split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            ids.append(int(chunk))
        except ValueError as exc:
            raise SystemExit(f"ADMIN_IDS: {chunk!r} — не число") from exc
    if not ids:
        raise SystemExit("ADMIN_IDS не задан: укажите хотя бы один Telegram ID")
    return tuple(ids)


@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_ids: tuple[int, ...]
    db_path: str
    contact_username: str
    throttle_limit: int
    throttle_window_seconds: int

    def is_admin(self, user_id: int | None) -> bool:
        return user_id is not None and user_id in self.admin_ids


def load_config() -> Config:
    load_env_file(PROJECT_ROOT / ".env")

    token = os.environ.get("BOT_TOKEN", "").strip()
    if not token:
        raise SystemExit(
            "BOT_TOKEN не задан. Скопируйте .env.example в .env и вставьте токен "
            "от @BotFather"
        )

    return Config(
        bot_token=token,
        admin_ids=_parse_admin_ids(os.environ.get("ADMIN_IDS", "")),
        db_path=os.environ.get("DB_PATH", "data/orders.db"),
        contact_username=os.environ.get("CONTACT_USERNAME", "manager").lstrip("@"),
        throttle_limit=int(os.environ.get("THROTTLE_LIMIT", "3")),
        throttle_window_seconds=int(os.environ.get("THROTTLE_WINDOW_SECONDS", "3600")),
    )
