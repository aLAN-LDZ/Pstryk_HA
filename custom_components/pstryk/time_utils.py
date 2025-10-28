from __future__ import annotations

from datetime import datetime, timedelta, timezone, date
from typing import Tuple

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None


def euwarsaw() -> timezone:
    """Zwraca strefę czasową Europe/Warsaw lub fallback UTC+1 (bez DST)."""
    if ZoneInfo:
        return ZoneInfo("Europe/Warsaw")
    return timezone(timedelta(hours=1))


def local_day_window_utc(d: date) -> Tuple[datetime, datetime]:
    """Zwraca (start_utc, end_utc) pełnej doby lokalnej [00:00, 24:00) w UTC."""
    tz = euwarsaw()
    start_local = datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=tz)
    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


def local_day_window_utc_ms(d: date) -> Tuple[datetime, datetime]:
    """Zwraca (start_utc, end_utc) pełnej doby lokalnej [00:00:00.000, 23:59:59.999] w UTC."""
    tz = euwarsaw()
    start_local = datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=tz)
    end_local = start_local + timedelta(days=1) - timedelta(milliseconds=1)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)