from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the CLI."""

    model_config = SettingsConfigDict(
        env_prefix="FUSION_",
        env_nested_delimiter="__",
        env_file=".env",
        extra="ignore",
    )

    oracle_base_url: str = "https://eclf.fa.em2.oraclecloud.com"
    oracle_resource_version: str = "ee7b954c-bcc8-4b41-bf6a-3a136a30223e"
    oracle_api_version: str = "11.13.18.05:9"
    oracle_person_id: str | None = None
    oracle_timeout: float = 30.0
    oracle_field_project: str = "300004857566518"
    oracle_field_task: str = "300004857566519"
    oracle_field_time_type: str = "300004857566520"
    oracle_field_location: str = "300004857566523"
    oracle_field_payroll_time_type: str = "300004857566527"
    oracle_field_absence: str = "300004857566525"
    oracle_field_assignment: str = "300004857566486"
    oracle_field_business_unit: str = "300004857566490"
    oracle_field_entry_source: str = "300004857566484"
    oracle_field_entry_context: str = "300004857566482"
    oracle_assignment_value: str = "300000002560077"
    oracle_business_unit_value: str = "300000001598197"
    oracle_entry_source_value: str = "ST"
    oracle_entry_context_value: str = "300000001656097"
    cache_ttl_hours: int = 24
    app_dir: Path = Field(default_factory=lambda: Path.home() / ".fusion-cli")

    @property
    def cache_dir(self) -> Path:
        return self.app_dir / "cache"

    @property
    def secrets_file(self) -> Path:
        return self.app_dir / "session.json"

    @property
    def browser_profile_dir(self) -> Path:
        return self.app_dir / "browser-profile"


def load_settings() -> Settings:
    return Settings()
