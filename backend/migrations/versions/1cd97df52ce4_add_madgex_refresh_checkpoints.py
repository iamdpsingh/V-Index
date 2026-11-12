"""Add checkpoints for large Madgex refreshes."""

import sqlalchemy as sa
from alembic import op

revision = "1cd97df52ce4"
down_revision = "91a1992d6635"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "madgex_refreshes",
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("roster", sa.JSON(), nullable=False),
        sa.Column("jobs", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("source_id"),
    )


def downgrade() -> None:
    op.drop_table("madgex_refreshes")
