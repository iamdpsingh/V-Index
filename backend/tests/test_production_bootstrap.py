from datetime import UTC, datetime

from sqlalchemy import func, select
from vindex.db import Source
from vindex.ingest import aware

from scripts import register_verified_sources as registration
from scripts import start_production_worker as startup


def test_reviewed_source_registration_is_idempotent_and_preserves_schedules(database, monkeypatch):
    monkeypatch.setattr(registration, "Session", database)
    preview = registration.register_sources()
    with database() as session:
        assert session.scalar(select(func.count()).select_from(Source)) == 0
    first = registration.register_sources(apply=True)
    assert first["new_sources"] == preview["new_sources"] > 0
    assert first["verified_platforms"] == 71
    sentinel = datetime(2030, 1, 1, tzinfo=UTC)
    with database() as session:
        row = session.scalar(select(Source).limit(1))
        row.next_check, row.failures = sentinel, 3
        source_id = row.id
        session.commit()
    again = registration.register_sources(apply=True)
    assert again["new_sources"] == 0
    with database() as session:
        row = session.get(Source, source_id)
        assert aware(row.next_check) == sentinel and row.failures == 3
        assert session.scalar(select(func.count()).select_from(Source)) == first["new_sources"]


def test_worker_rejects_invalid_config_without_printing_connections(monkeypatch, caplog):
    monkeypatch.setenv("DATABASE_URL", "https://PRIVATE_CREDENTIAL_CANARY@example.com")
    monkeypatch.setenv("REDIS_URL", "https://PRIVATE_CREDENTIAL_CANARY@example.com")
    assert startup.main() == 1
    assert "CANARY" not in caplog.text
