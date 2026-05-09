from fusionctl.services.timecard_payloads import entries_to_preserve_on_clear


def test_entries_to_preserve_on_clear_keeps_public_holidays_and_absences() -> None:
    regular_entry = {
        "TimeEntryId": "regular",
        "timeCardFieldValues": {
            "items": [{"TimeCardFieldId": "time-type", "DisplayValue": "Regular"}]
        },
    }
    public_holiday_entry = {
        "TimeEntryId": "holiday",
        "timeCardFieldValues": {
            "items": [{"TimeCardFieldId": "time-type", "DisplayValue": "Public Holiday"}]
        },
    }
    absence_entry = {
        "TimeEntryId": "leave",
        "AbsenceEntryFlag": True,
        "timeCardFieldValues": {
            "items": [{"TimeCardFieldId": "absence", "DisplayValue": "Annual Leave MD"}]
        },
    }

    preserved = entries_to_preserve_on_clear([regular_entry, public_holiday_entry, absence_entry])

    assert [entry["TimeEntryId"] for entry in preserved] == ["holiday", "leave"]


def test_entries_to_preserve_on_clear_handles_flat_field_value_arrays() -> None:
    public_holiday_entry = {
        "TimeEntryId": "holiday",
        "timeCardFieldValues": [{"TimeCardFieldId": "time-type", "Value": "Public Holiday"}],
    }

    assert entries_to_preserve_on_clear([public_holiday_entry]) == [public_holiday_entry]
