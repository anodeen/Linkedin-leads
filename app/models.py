from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from urllib.parse import urlparse


class DataSource(str, Enum):
    OFFICIAL_API = "official_api"
    VETTED_PROVIDER = "vetted_provider"


@dataclass(slots=True)
class InboundLead:
    full_name: str
    title: str
    company: str
    profile_url: str
    source: DataSource

    def validate(self) -> None:
        if len(self.full_name.strip()) < 2:
            raise ValueError("full_name must be at least 2 characters")
        if len(self.title.strip()) < 2:
            raise ValueError("title must be at least 2 characters")
        if len(self.company.strip()) < 2:
            raise ValueError("company must be at least 2 characters")
        parsed = urlparse(self.profile_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("profile_url must be a valid http(s) URL")


@dataclass(slots=True)
class Lead:
    id: int
    full_name: str
    title: str
    company: str
    profile_url: str
    source: DataSource
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class IngestLeadsResponse:
    provider_name: str
    accepted: int
    rejected: int
    lead_ids: list[int]
