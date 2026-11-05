import os
import uuid
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from vindex.db import Base, Source


@pytest.fixture(
    params=[
        "sqlite",
        pytest.param(
            "postgresql",
            marks=pytest.mark.skipif(
                not os.getenv("TEST_DATABASE_URL"),
                reason="Set TEST_DATABASE_URL for PostgreSQL integration tests",
            ),
        ),
    ]
)
def database(request):
    if request.param == "sqlite":
        engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )

        @event.listens_for(engine, "connect")
        def enable_foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")

        Base.metadata.create_all(engine)
        yield sessionmaker(engine, expire_on_commit=False)
        engine.dispose()
        return
    url = os.environ["TEST_DATABASE_URL"]
    admin = create_engine(url)
    if admin.dialect.name != "postgresql":
        raise ValueError("TEST_DATABASE_URL must use PostgreSQL")
    schema = "vindex_test_" + uuid.uuid4().hex
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    try:
        config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
        with engine.begin() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
        yield sessionmaker(engine, expire_on_commit=False)
    finally:
        engine.dispose()
        # Only the unique schema created by this fixture is removed, never existing data.
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


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
