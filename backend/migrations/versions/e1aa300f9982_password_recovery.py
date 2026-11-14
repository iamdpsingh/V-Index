"""Add expiring password recovery challenges."""

import sqlalchemy as sa
from alembic import op

revision = "e1aa300f9982"
down_revision = "4cc4057f6ac1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("accounts", sa.Column("password_reset_hash", sa.String(64)))
    op.add_column("accounts", sa.Column("password_reset_expires_at", sa.DateTime(timezone=True)))


def downgrade() -> None:
    with op.batch_alter_table("accounts") as batch:
        batch.drop_column("password_reset_expires_at")
        batch.drop_column("password_reset_hash")
