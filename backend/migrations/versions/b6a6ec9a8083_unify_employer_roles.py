"""Consolidate employer roles."""

import sqlalchemy as sa
from alembic import op

revision = "b6a6ec9a8083"
down_revision = "a865e43b7fa2"
branch_labels = None
depends_on = None

accounts = sa.table("accounts", sa.column("role", sa.String()))


def upgrade():
    op.execute(
        accounts.update()
        .where(accounts.c.role.in_(("agency", "company", "job_poster")))
        .values(role="employer")
    )


def downgrade():
    # The three original roles had identical permissions.
    op.execute(accounts.update().where(accounts.c.role == "employer").values(role="job_poster"))
