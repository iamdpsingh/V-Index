"""Accelerate existing substring search with PostgreSQL trigram indexes."""

import sqlalchemy as sa
from alembic import op

revision = "f0d9dfe21a36"
down_revision = "e8f36d47b501"
branch_labels = None
depends_on = None

FIELDS = ("title", "description", "company", "location")


def upgrade():
    connection = op.get_bind()
    if connection.dialect.name != "postgresql":
        return
    schema = connection.scalar(
        sa.text(
            "SELECT n.nspname FROM pg_extension e JOIN pg_namespace n "
            "ON n.oid = e.extnamespace WHERE e.extname = 'pg_trgm'"
        )
    )
    if schema is None:
        op.execute("CREATE EXTENSION pg_trgm WITH SCHEMA public")
        schema = "public"
    quoted_schema = connection.dialect.identifier_preparer.quote_schema(schema)
    for field in FIELDS:
        op.execute(
            sa.text(
                f"CREATE INDEX ix_jobs_{field}_trgm ON jobs USING gin "
                f"((CAST(data ->> '{field}' AS VARCHAR)) {quoted_schema}.gin_trgm_ops)"
            )
        )


def downgrade():
    if op.get_bind().dialect.name != "postgresql":
        return
    for field in reversed(FIELDS):
        op.drop_index(f"ix_jobs_{field}_trgm", table_name="jobs")
