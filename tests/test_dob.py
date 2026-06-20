from datetime import date

import pytest

from gg_generator.identity.dob import generate_dob


def test_respects_year_range():
    ref = date(2026, 6, 19)
    for _ in range(200):
        iso, age = generate_dob(1980, 1990, today=ref)
        year = int(iso[:4])
        assert 1980 <= year <= 1990
        assert age == ref.year - year - (0 if (ref.month, ref.day) >= _md(iso) else 1)


def test_default_floor_is_1980():
    ref = date(2026, 6, 19)
    iso, _ = generate_dob(today=ref)
    assert int(iso[:4]) >= 1980


def test_default_ceiling_is_adult():
    ref = date(2026, 6, 19)
    for _ in range(50):
        _, age = generate_dob(today=ref)
        assert age >= 18


def test_inverted_range_raises():
    with pytest.raises(ValueError):
        generate_dob(1995, 1990, today=date(2026, 6, 19))


def _md(iso: str) -> tuple[int, int]:
    return int(iso[5:7]), int(iso[8:10])
