import math
import re
from datetime import datetime
from ipaddress import ip_address
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

    @field_validator("external_id", "title", "company", mode="before")
    @classmethod
    def required_text(cls, value: Any) -> Any:
        return value.strip() if isinstance(value, str) else value

    @field_validator("source_url", "application_url")
    @classmethod
    def public_link(cls, value: str) -> str:
        try:
            parsed = urlsplit(value)
            host = (parsed.hostname or "").rstrip(".").casefold()
            valid = (
                parsed.scheme == "https"
                and host
                and not parsed.username
                and not parsed.password
                and parsed.port in (None, 443)
                and not re.search(r"[\x00-\x20\x7f\\]", value)
                and not host.endswith((".localhost", ".local", ".internal"))
                and host not in {"localhost", "metadata.google.internal"}
            )
            try:
                address = ip_address(host)
            except ValueError:
                if re.fullmatch(r"[0-9.]+|0x[0-9a-f]+", host):
                    valid = False
            else:
                valid = valid and address.is_global
        except ValueError:
            valid = False
        if not valid:
            raise ValueError("Expected an HTTPS link without credentials")
        return value

    @field_validator("salary")
    @classmethod
    def finite_compensation(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        def check(item: Any) -> None:
            if isinstance(item, float) and not math.isfinite(item):
                raise ValueError("Salary metadata must contain finite JSON numbers")
            if isinstance(item, dict):
                for child in item.values():
                    check(child)
            elif isinstance(item, list):
                for child in item:
                    check(child)

        check(value)
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
    first_seen_at: datetime | None = None
    last_changed_at: datetime | None = None


class SalaryRangeOut(BaseModel):
    min: float | None = None
    max: float | None = None
    currency: str | None = None
    period: str | None = None
    label: str | None = None


class SalaryOut(BaseModel):
    min: float | None = None
    max: float | None = None
    currency: str | None = None
    period: str | None = None
    text: str | None = None
    ranges: list[SalaryRangeOut] = Field(default_factory=list)
    source: dict[str, Any] = Field(default_factory=dict)


class JobSummaryOut(BaseModel):
    id: int
    external_id: str
    title: str
    company: str
    quality_flags: list[str] = Field(default_factory=list)
    field_sources: dict[str, str] = Field(default_factory=dict)
    location: str
    source_url: str
    application_url: str
    employment_type: str | None
    remote_status: str | None
    employment_type_source: str | None = None
    remote_status_source: str | None = None
    salary: SalaryOut | None
    published_at: datetime | None
    first_seen_at: datetime
    last_changed_at: datetime
    last_checked_at: datetime | None = None
    sources: list[ProvenanceOut]

    @field_validator("source_url", "application_url")
    @classmethod
    def public_link(cls, value: str) -> str:
        return JobInput.public_link(value)


class JobOut(JobSummaryOut):
    description: str


class SearchSummaryOut(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[JobSummaryOut]


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
