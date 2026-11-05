from datetime import datetime
from typing import Any
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, field_validator


class JobInput(BaseModel):
    external_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    company: str = Field(min_length=1)
    description: str
    quality_flags: list[str] = Field(default_factory=list)
    location: str = ""
    source_url: str
    application_url: str
    employment_type: str | None = None
    remote_status: str | None = None
    salary: dict[str, Any] | None = None
    published_at: datetime | None = None
    raw: dict[str, Any] = Field(default_factory=dict)

    @field_validator("source_url", "application_url")
    @classmethod
    def public_link(cls, value: str) -> str:
        parsed = urlsplit(value)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Expected an HTTPS link without credentials")
        return value


class Enumeration(BaseModel):
    jobs: list[JobInput]
    complete: bool = False


class SourceCreate(BaseModel):
    url: str = Field(max_length=2048)
    company: str = Field(min_length=1, max_length=200)
    refresh_minutes: int = Field(default=360, ge=60, le=10080)


class ProvenanceOut(BaseModel):
    source_id: int
    source_url: str
    application_url: str
    status: str
    last_checked_at: datetime


class JobOut(BaseModel):
    id: int
    external_id: str
    title: str
    company: str
    description: str
    quality_flags: list[str] = Field(default_factory=list)
    location: str
    source_url: str
    application_url: str
    employment_type: str | None
    remote_status: str | None
    salary: dict[str, Any] | None
    published_at: datetime | None
    first_seen_at: datetime
    last_changed_at: datetime
    sources: list[ProvenanceOut]


class SearchOut(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[JobOut]


class SourceOut(BaseModel):
    id: int
    provider: str
    slug: str
    company: str
    url: str
    refresh_minutes: int
    next_check: datetime
    failures: int


class RunOut(BaseModel):
    id: int
    source_id: int
    started_at: datetime
    finished_at: datetime | None
    status: str
    count: int
    error: str | None
