import os
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, UniqueConstraint, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


def now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class Source(Base):
    __tablename__ = "sources"
    __table_args__ = (UniqueConstraint("provider", "slug"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(50))
    slug: Mapped[str] = mapped_column(String(100))
    company: Mapped[str] = mapped_column(String(200))
    url: Mapped[str] = mapped_column(String(2048))
    refresh_minutes: Mapped[int] = mapped_column(default=360)
    next_check: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    failures: Mapped[int] = mapped_column(default=0)


class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[int] = mapped_column(primary_key=True)
    identity: Mapped[str] = mapped_column(String(64), unique=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    last_changed: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Observation(Base):
    __tablename__ = "observations"
    __table_args__ = (UniqueConstraint("source_id", "external_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), index=True)
    external_id: Mapped[str] = mapped_column(String(500))
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), index=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON)
    fingerprint: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(default="open")
    missing_count: Mapped[int] = mapped_column(default=0)
    missing_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    last_checked: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    last_changed: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Run(Base):
    __tablename__ = "fetch_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(default="running")
    count: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None]


class Event(Base):
    __tablename__ = "change_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    observation_id: Mapped[int] = mapped_column(ForeignKey("observations.id"))
    kind: Mapped[str]
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


engine = create_engine(os.getenv("DATABASE_URL", "sqlite:///vindex.db"))
Session = sessionmaker(engine, expire_on_commit=False)
