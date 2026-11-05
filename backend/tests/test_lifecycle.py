from datetime import timedelta

import pytest
from sqlalchemy import func, select
from vindex.db import Event, Job, Observation, Source, now
from vindex.ingest import identity, ingest
from vindex.schemas import Enumeration, JobInput


def posting(**overrides):
    return JobInput(
        **{
            **dict(
                external_id="job-1",
                title="Engineer",
                company="Example",
                description="Build useful things",
                location="London",
                source_url="https://jobs.ashbyhq.com/example/job-1",
                application_url="https://jobs.ashbyhq.com/example/job-1/apply",
            ),
            **overrides,
        }
    )


def test_idempotent_update_close_and_reappear(database, source):
    start = now()
    with database() as s:
        batch = Enumeration(jobs=[posting()], complete=True)
        ingest(s, source, batch, start)
        s.commit()
        ingest(s, source, batch, start + timedelta(hours=1))
        s.commit()
        assert s.scalar(select(func.count()).select_from(Job)) == 1
        assert s.scalar(select(func.count()).select_from(Event)) == 1
        ingest(
            s,
            source,
            Enumeration(jobs=[posting(description="Changed")], complete=True),
            start + timedelta(hours=2),
        )
        s.commit()
        assert s.scalars(select(Event.kind)).all() == ["created", "updated"]
        empty = Enumeration(jobs=[], complete=True)
        ingest(s, source, empty, start + timedelta(hours=3))
        s.commit()
        obs = s.scalar(select(Observation))
        assert obs.status == "open"
        ingest(s, source, empty, start + timedelta(hours=4))
        s.commit()
        assert obs.status == "open"
        ingest(s, source, empty, start + timedelta(hours=27))
        s.commit()
        assert obs.status == "closed"
        ingest(s, source, batch, start + timedelta(hours=28))
        s.commit()
        assert obs.status == "open"
        assert obs.missing_count == 0
        assert s.scalars(select(Event.kind)).all() == ["created", "updated", "closed", "reopened"]


def test_partial_and_duplicate_snapshots_never_close(database, source):
    with database() as s:
        ingest(s, source, Enumeration(jobs=[posting()], complete=True))
        s.commit()
        with pytest.raises(ValueError, match="Incomplete"):
            ingest(s, source, Enumeration(jobs=[]))
        with pytest.raises(ValueError, match="Duplicate"):
            ingest(s, source, Enumeration(jobs=[posting(), posting()], complete=True))
        assert s.scalar(select(Observation)).missing_count == 0


def test_conservative_cross_source_dedupe_and_provenance(database, source):
    with database() as s:
        second = Source(
            provider="lever", slug="example", company="Example", url="https://jobs.lever.co/example"
        )
        s.add(second)
        s.flush()
        ingest(s, source, Enumeration(jobs=[posting()], complete=True))
        ingest(
            s, second, Enumeration(jobs=[posting(external_id="different-source-id")], complete=True)
        )
        s.commit()
        assert s.scalar(select(func.count()).select_from(Job)) == 1
        assert s.scalar(select(func.count()).select_from(Observation)) == 2
        ingest(
            s,
            second,
            Enumeration(
                jobs=[
                    posting(
                        external_id="other-role",
                        application_url="https://jobs.lever.co/example/other/apply",
                    )
                ],
                complete=True,
            ),
        )
        s.commit()
        assert s.scalar(select(func.count()).select_from(Job)) == 2


def test_identity_preserves_requisition_query_and_distinct_location():
    assert identity(posting()) == identity(
        posting(application_url=posting().application_url + "?utm_campaign=test")
    )
    assert identity(posting()) != identity(
        posting(application_url=posting().application_url + "?jobId=2")
    )
    assert identity(posting()) != identity(posting(location="Paris"))
