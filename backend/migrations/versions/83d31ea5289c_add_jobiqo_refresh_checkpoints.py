"""Add checkpoints for large Jobiqo refreshes."""

import sqlalchemy as sa
from alembic import op

revision = "83d31ea5289c"
down_revision = "1cd97df52ce4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "jobiqo_refreshes",
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("roster", sa.JSON(), nullable=False),
        sa.Column("jobs", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("source_id"),
    )


def downgrade() -> None:
    op.drop_table("jobiqo_refreshes")
