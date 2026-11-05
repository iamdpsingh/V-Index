import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from vindex.db import Base, Source


@pytest.fixture
def database():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    yield factory
    engine.dispose()


@pytest.fixture
def source(database):
    with database() as session:
        item = Source(
            provider="ashby",
            slug="sample",
            company="Example",
            url="https://jobs.ashbyhq.com/sample",
        )
        session.add(item)
        session.commit()
        return item
