from datetime import date
from pathlib import Path

import httpx
import pytest

from fusionctl.services.holiday_calendar import (
    HolidayCalendar,
    PublicHoliday,
    load_holidays,
    parse_zilelibere_holidays,
)


ZILELIBERE_SAMPLE = """
<html>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Dataset",
  "hasPart": [
    {"@type": "Event", "name": "Ziua Internațională a Femeii", "startDate": "2026-03-08"},
    {"@type": "Event", "name": "Ziua Europei", "startDate": "2026-05-09"},
    {"@type": "Event", "name": "Hramul Chișinăului", "startDate": "2026-10-14"}
  ]
}
</script>
</html>
"""


def test_parse_zilelibere_holidays_excludes_regional_chisinau_holiday() -> None:
    holidays = parse_zilelibere_holidays(ZILELIBERE_SAMPLE, 2026)

    assert holidays == [
        PublicHoliday(date=date(2026, 3, 8), name="Ziua Internațională a Femeii"),
        PublicHoliday(date=date(2026, 5, 9), name="Ziua Europei"),
    ]


def test_load_holidays_reads_fresh_working_directory_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / ".fusionctl" / "holiday-calendars" / "moldova-2026.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        """
{
  "calendar": "moldova",
  "year": 2026,
  "source": "https://zilelibere.md/2026/",
  "fetched_at": "2026-05-09T00:00:00+00:00",
  "holidays": [{"date": "2026-05-09", "name": "Ziua Europei"}]
}
""".strip(),
        encoding="utf-8",
    )

    def fail_fetch(calendar: HolidayCalendar, year: int) -> list[PublicHoliday]:
        raise AssertionError("fresh cache should be used")

    monkeypatch.setattr("fusionctl.services.holiday_calendar.fetch_holidays", fail_fetch)

    result = load_holidays(HolidayCalendar.MOLDOVA, 2026, cwd=tmp_path)

    assert result.refreshed is False
    assert result.cache_path == path
    assert result.holidays == [PublicHoliday(date=date(2026, 5, 9), name="Ziua Europei")]


def test_load_holidays_falls_back_to_stale_cache_on_refresh_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / ".fusionctl" / "holiday-calendars" / "moldova-2026.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        """
{
  "calendar": "moldova",
  "year": 2026,
  "source": "https://zilelibere.md/2026/",
  "fetched_at": "2026-05-09T00:00:00+00:00",
  "holidays": [{"date": "2026-03-08", "name": "Ziua Internațională a Femeii"}]
}
""".strip(),
        encoding="utf-8",
    )

    def fail_fetch(calendar: HolidayCalendar, year: int) -> list[PublicHoliday]:
        raise httpx.ConnectError("offline")

    monkeypatch.setattr("fusionctl.services.holiday_calendar.fetch_holidays", fail_fetch)

    result = load_holidays(
        HolidayCalendar.MOLDOVA,
        2026,
        refresh=True,
        cwd=tmp_path,
    )

    assert result.refreshed is False
    assert result.holidays == [
        PublicHoliday(date=date(2026, 3, 8), name="Ziua Internațională a Femeii")
    ]
