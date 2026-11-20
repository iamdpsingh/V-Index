"""Check a hosted PostgreSQL schema; apply migrations only with --migrate.

Connection strings are accepted through DATABASE_URL or a hidden --prompt,
never command arguments. Errors omit SQL, parameters and connection details.
"""

import argparse
import getpass
import json
import os
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import NullPool

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompt", action="store_true", help="Read URL without echoing it")
    parser.add_argument("--migrate", action="store_true", help="Apply pending Alembic migrations")
    args = parser.parse_args()
    raw = (
        getpass.getpass("Production PostgreSQL connection URL (hidden): ")
        if args.prompt
        else os.getenv("DATABASE_URL", "")
    )
    if not raw:
        print("Set DATABASE_URL privately or use --prompt. No database was changed.")
        return 2
    try:
        url = make_url(raw.strip())
        if url.drivername in {"postgres", "postgresql"}:
            url = url.set(drivername="postgresql+psycopg")
        if url.drivername != "postgresql+psycopg":
            print(
                "This check requires PostgreSQL with the psycopg driver; no database was changed."
            )
            return 2
    except Exception:
        print("Invalid connection URL; no database was changed.")
        return 2
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "backend/migrations"))
    sys.path.insert(0, str(ROOT / "backend"))
    # The migration environment imports existing models. Prevent its default SQLite URL.
    os.environ["DATABASE_URL"] = url.render_as_string(hide_password=False)
    engine = create_engine(url, poolclass=NullPool, connect_args={"connect_timeout": 10})
    try:
        heads = set(ScriptDirectory.from_config(config).get_heads())
        with engine.connect() as connection:
            current = set(MigrationContext.configure(connection).get_current_heads())
            print(
                json.dumps(
                    {
                        "connection": "ok",
                        "schema_at_head": current == heads,
                        "migration_requested": args.migrate,
                    }
                )
            )
        if args.migrate and current != heads:
            # One operator action, never an application import or per-request migration.
            with engine.begin() as connection:
                config.attributes["connection"] = connection
                command.upgrade(config, "head")
        from vindex.accounts import models  # noqa: F401
        from vindex.db import Base

        with engine.connect() as connection:
            current = set(MigrationContext.configure(connection).get_current_heads())
            inspector = inspect(connection)
            missing_tables, missing_columns = [], []
            for table in Base.metadata.sorted_tables:
                if not inspector.has_table(table.name):
                    missing_tables.append(table.name)
                    continue
                actual = {column["name"] for column in inspector.get_columns(table.name)}
                missing_columns.extend(
                    f"{table.name}.{column.name}"
                    for column in table.columns
                    if column.name not in actual
                )
            ready = current == heads and not missing_tables and not missing_columns
            print(
                json.dumps(
                    {
                        "schema_at_head": current == heads,
                        "missing_tables": missing_tables,
                        "missing_columns": missing_columns,
                        "ready": ready,
                    }
                )
            )
            if not ready:
                print(
                    "Schema is not ready. Review the result; use --migrate for pending migrations. Do not drop tables or stamp migrations to hide errors."
                )
            return 0 if ready else 1
    except SQLAlchemyError as error:
        code = getattr(getattr(error, "orig", None), "sqlstate", None)
        code = code if isinstance(code, str) and len(code) == 5 and code.isalnum() else None
        print(
            json.dumps(
                {"database_check": "failed", "error_kind": type(error).__name__, "sqlstate": code}
            )
        )
        return 1
    except Exception as error:
        print(json.dumps({"database_check": "failed", "error_kind": type(error).__name__}))
        return 1
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
