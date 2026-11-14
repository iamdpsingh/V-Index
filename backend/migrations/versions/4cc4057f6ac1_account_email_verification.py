"""Add email verification state to accounts."""

import sqlalchemy as sa
from alembic import op

revision = "4cc4057f6ac1"
down_revision = "83d31ea5289c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("accounts", sa.Column("email_verified_at", sa.DateTime(timezone=True)))
    op.add_column("accounts", sa.Column("email_code_hash", sa.String(64)))
    op.add_column("accounts", sa.Column("email_code_expires_at", sa.DateTime(timezone=True)))


def downgrade() -> None:
    with op.batch_alter_table("accounts") as batch:
        batch.drop_column("email_code_expires_at")
        batch.drop_column("email_code_hash")
        batch.drop_column("email_verified_at")
