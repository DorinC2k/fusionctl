from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from datetime import date as Date
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any

import httpx


DEFAULT_CACHE_MAX_AGE_DAYS = 30
SOURCE_TIMEOUT_SECONDS = 20.0


class HolidayCalendar(str, Enum):
    MOLDOVA = "moldova"


@dataclass(frozen=True)
class PublicHoliday:
    date: Date
    name: str


@dataclass(frozen=True)
class HolidayCacheResult:
    holidays: list[PublicHoliday]
    cache_path: Path
    refreshed: bool


def cache_root(*, cwd: Path | None = None) -> Path:
    return (cwd or Path.cwd()) / ".fusionctl" / "holiday-calendars"


def load_holidays(
    calendar: HolidayCalendar,
    year: int,
    *,
    refresh: bool = False,
    max_age_days: int = DEFAULT_CACHE_MAX_AGE_DAYS,
    cwd: Path | None = None,
) -> HolidayCacheResult:
    """Load public holidays from the working-directory cache, refreshing when needed."""
    path = cache_path(calendar, year, cwd=cwd)
    if not refresh and path.exists() and not _is_cache_stale(path, max_age_days):
        return HolidayCacheResult(holidays=_read_cache(path), cache_path=path, refreshed=False)

    try:
        holidays = fetch_holidays(calendar, year)
    except httpx.HTTPError:
        if path.exists():
            return HolidayCacheResult(holidays=_read_cache(path), cache_path=path, refreshed=False)
        raise

    _write_cache(path, calendar, year, holidays)
    return HolidayCacheResult(holidays=holidays, cache_path=path, refreshed=True)


def cache_path(calendar: HolidayCalendar, year: int, *, cwd: Path | None = None) -> Path:
    return cache_root(cwd=cwd) / f"{calendar.value}-{year}.json"


def fetch_holidays(calendar: HolidayCalendar, year: int) -> list[PublicHoliday]:
    if calendar is HolidayCalendar.MOLDOVA:
        url = f"https://zilelibere.md/{year}/"
        response = httpx.get(url, follow_redirects=True, timeout=SOURCE_TIMEOUT_SECONDS)
        response.raise_for_status()
        return parse_zilelibere_holidays(response.text, year)
    raise ValueError(f"Unsupported holiday calendar: {calendar.value}")


def parse_zilelibere_holidays(page: str, year: int) -> list[PublicHoliday]:
    """Parse zilelibere.md JSON-LD event data for national Moldova holidays."""
    scripts = re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        page,
        flags=re.DOTALL | re.IGNORECASE,
    )
    for script in scripts:
        data = json.loads(html.unescape(script.strip()))
        events = data.get("hasPart") if isinstance(data, dict) else None
        if not isinstance(events, list):
            continue
        holidays = [_event_to_holiday(event, year) for event in events]
        return sorted(
            [holiday for holiday in holidays if holiday is not None], key=lambda item: item.date
        )
    raise ValueError("Could not find holiday JSON-LD data")


def _event_to_holiday(event: Any, year: int) -> PublicHoliday | None:
    if not isinstance(event, dict):
        return None
    name = str(event.get("name") or "").strip()
    start_date = str(event.get("startDate") or "").strip()
    if not name or not start_date or _is_regional_holiday(name):
        return None
    holiday_date = Date.fromisoformat(start_date)
    if holiday_date.year != year:
        return None
    return PublicHoliday(date=holiday_date, name=name)


def _is_regional_holiday(name: str) -> bool:
    return "hramul chișinăului" in name.casefold()


def _is_cache_stale(path: Path, max_age_days: int) -> bool:
    if max_age_days <= 0:
        return True
    modified_at = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return datetime.now(timezone.utc) - modified_at > timedelta(days=max_age_days)


def _read_cache(path: Path) -> list[PublicHoliday]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [
        PublicHoliday(date=Date.fromisoformat(item["date"]), name=str(item["name"]))
        for item in payload["holidays"]
    ]


def _write_cache(
    path: Path,
    calendar: HolidayCalendar,
    year: int,
    holidays: list[PublicHoliday],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "calendar": calendar.value,
        "year": year,
        "source": f"https://zilelibere.md/{year}/",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "holidays": [
            {
                "date": holiday.date.isoformat(),
                "name": holiday.name,
            }
            for holiday in holidays
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
