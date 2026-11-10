"""Тесты валидации ввода: чистая логика, без aiogram."""

from __future__ import annotations

import pytest

from app.texts import normalize_description, normalize_name, normalize_phone


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Иван", "Иван"),
        ("  Иван   Петров ", "Иван Петров"),
        ("Я", None),
        ("", None),
        ("a" * 81, None),
    ],
)
def test_normalize_name(raw, expected):
    assert normalize_name(raw) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("+79991234567", "+79991234567"),
        ("89991234567", "+79991234567"),
        ("+7 (999) 123-45-67", "+79991234567"),
        ("123", None),
        ("телефон", None),
        ("+7" + "1" * 20, None),
    ],
)
def test_normalize_phone(raw, expected):
    assert normalize_phone(raw) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Нужен бот для заявок", "Нужен бот для заявок"),
        ("коротко", None),
        ("x" * 1201, None),
    ],
)
def test_normalize_description(raw, expected):
    assert normalize_description(raw) == expected
