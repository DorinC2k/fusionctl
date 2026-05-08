from datetime import datetime, timezone

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Session(BaseModel):
    """Authentication session metadata for Oracle Fusion Cloud."""

    token: str = Field(..., min_length=1)
    source: str = "manual-cookie"
    username: str | None = None
    person_id: str | None = None
    person_number: str | None = None
    expiry: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)

    @property
    def is_valid(self) -> bool:
        if self.expiry is None:
            return True
        return datetime.now(timezone.utc) < self.expiry


class CacheMetadata(BaseModel):
    """Metadata for cached data."""

    last_fetched: datetime = Field(default_factory=utc_now)
    ttl_hours: int = Field(24, ge=1, le=720)
    version: str = "1.0"
    oracle_base_url: str = "https://eclf.fa.em2.oraclecloud.com"

    def is_expired(self) -> bool:
        age_hours = (datetime.now(timezone.utc) - self.last_fetched).total_seconds() / 3600
        return age_hours > self.ttl_hours
