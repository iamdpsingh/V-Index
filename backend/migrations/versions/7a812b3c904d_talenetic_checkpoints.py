"""Persist large Talenetic rosters and independently checkpoint each detail."""

import sqlalchemy as sa
from alembic import op

revision = "7a812b3c904d"
down_revision = "f0d9dfe21a36"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "talenetic_refreshes",
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("roster", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("source_id"),
    )
    op.create_table(
        "talenetic_details",
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("external_id", sa.String(500), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_id"], ["talenetic_refreshes.source_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("source_id", "external_id"),
    )


def downgrade() -> None:
    op.drop_table("talenetic_details")
    op.drop_table("talenetic_refreshes")
