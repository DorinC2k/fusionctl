from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the CLI."""

    model_config = SettingsConfigDict(env_prefix="FUSION_", env_nested_delimiter="__")

    oracle_base_url: str = "https://eclf.fa.em2.oraclecloud.com"
    oracle_timeout: float = 30.0
    cache_ttl_hours: int = 24
    app_dir: Path = Field(default_factory=lambda: Path.home() / ".fusion-cli")

    @property
    def cache_dir(self) -> Path:
        return self.app_dir / "cache"

    @property
    def secrets_file(self) -> Path:
        return self.app_dir / "session.json"


def load_settings() -> Settings:
    return Settings()
