"""Date-of-birth generation constrained to a birth-year range.

randomuser.me can't constrain age, so we generate the DOB locally. The floor
defaults to 1980; the ceiling defaults to "must be a legal adult" (>= 18).
"""

from __future__ import annotations

from datetime import date

from faker import Faker

DEFAULT_MIN_YEAR = 1980
_ADULT_AGE = 18
_fake = Faker("en_US")


def _years_ago(d: date, years: int) -> date:
    """``d`` shifted back ``years`` years, handling the Feb-29 edge case."""
    try:
        return d.replace(year=d.year - years)
    except ValueError:  # Feb 29 -> non-leap target year
        return d.replace(year=d.year - years, day=28)


def generate_dob(
    min_year: int = DEFAULT_MIN_YEAR,
    max_year: int | None = None,
    *,
    today: date | None = None,
) -> tuple[str, int]:
    """Return ``(iso_date, age)`` for a birthdate in ``[min_year, max_year]``.

    Args:
        min_year: earliest birth year (inclusive). Defaults to 1980.
        max_year: latest birth year (inclusive). Defaults to the most recent
            year that still yields an 18+ adult.
        today: reference date for age math (injectable for tests).

    Raises:
        ValueError: if the resulting range is empty.
    """
    today = today or date.today()
    start = date(min_year, 1, 1)
    if max_year is None:
        # Exact "18 years ago today" so the default always yields a legal adult.
        end = _years_ago(today, _ADULT_AGE)
    else:
        if max_year < min_year:
            raise ValueError(f"max_year ({max_year}) is before min_year ({min_year})")
        end = min(date(max_year, 12, 31), today)
    if end < start:
        raise ValueError("birth-year range produces no valid dates")

    born = _fake.date_between_dates(date_start=start, date_end=end)
    age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    return born.isoformat(), age
