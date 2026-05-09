from urllib.parse import quote


class OracleEndpoints:
    def __init__(self, base_url: str, resource_version: str, api_version: str = "11.13.18.05:9") -> None:
        self.base_url = base_url.rstrip("/")
        self.resource_version = resource_version
        self.api_version = api_version

    @property
    def api_root(self) -> str:
        rv = self.resource_version if self.resource_version.startswith("rv:") else f"rv:{self.resource_version}"
        return f"{self.base_url}/hcmRestApi/rest/{quote(rv, safe=':')}/en/{quote(self.api_version, safe='.:')}"

    def employment_info(self) -> str:
        return f"{self.api_root}/employmentInfo"

    def timecards_search(self) -> str:
        return f"{self.api_root}/timeCards/action/findByAdvancedSearchQuery"

    def timecard(self, timecard_id: str) -> str:
        return f"{self.api_root}/timeCards/{quote(timecard_id)}"

    def timecard_entry_details(self) -> str:
        return f"{self.api_root}/timeCardEntryDetails"

    def timecard_field_values(self) -> str:
        return f"{self.api_root}/timeCardFieldValues"

    def tokenrelay(self) -> str:
        return f"{self.base_url}/fscmRestApi/tokenrelay"
