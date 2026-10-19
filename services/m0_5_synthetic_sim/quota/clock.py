"""Pacific-time day boundaries (Gemini RPD resets at midnight Pacific).

Implemented with the US DST rule instead of zoneinfo: the Windows Python used by
this repo has no tzdata, and adding a dependency for one zone is not worth it.
DST runs from the 2nd Sunday of March 02:00 PST (10:00 UTC) to the
1st Sunday of November 02:00 PDT (09:00 UTC).
"""
from __future__ import annotations

from datetime import UTC, date, datetime, timedelta


def _nth_sunday(year: int, month: int, n: int) -> date:
    first = date(year, month, 1)
    return first + timedelta(days=(6 - first.weekday()) % 7 + 7 * (n - 1))


def pacific_offset_hours(t: datetime) -> int:
    t = t.astimezone(UTC)
    start = datetime.combine(_nth_sunday(t.year, 3, 2), datetime.min.time(), UTC) + timedelta(hours=10)
    end = datetime.combine(_nth_sunday(t.year, 11, 1), datetime.min.time(), UTC) + timedelta(hours=9)
    return -7 if start <= t < end else -8


def _pacific_midnight(d: date) -> datetime:
    naive = datetime.combine(d, datetime.min.time(), UTC)
    for off in (7, 8):
        cand = naive + timedelta(hours=off)
        if pacific_offset_hours(cand) == -off:
            return cand
    return naive + timedelta(hours=8)  # unreachable with the US rule


def pacific_date(t: datetime) -> date:
    t = t.astimezone(UTC)
    return (t + timedelta(hours=pacific_offset_hours(t))).date()


def pacific_day_start(t: datetime) -> datetime:
    return _pacific_midnight(pacific_date(t))


def next_pacific_day_start(t: datetime) -> datetime:
    # Pacific days are 23-25 h long, so start + 26 h always lands inside the next day.
    return pacific_day_start(pacific_day_start(t) + timedelta(hours=26))


def pacific_month_start(t: datetime) -> datetime:
    return _pacific_midnight(pacific_date(t).replace(day=1))
