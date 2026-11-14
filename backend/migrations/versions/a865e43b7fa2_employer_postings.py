"""Add account roles and employer postings."""

import sqlalchemy as sa
from alembic import op

revision = "a865e43b7fa2"
down_revision = "c1f43ed058e0"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("accounts", sa.Column("role", sa.String(20)))
    op.create_table(
        "account_oauth_identities",
        sa.Column("provider", sa.String(20), primary_key=True),
        sa.Column("subject", sa.String(255), primary_key=True),
        sa.Column(
            "account_id",
            sa.String(36),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_account_oauth_identities_account_id", "account_oauth_identities", ["account_id"]
    )
    op.create_table(
        "employer_postings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "account_id",
            sa.String(36),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id")),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
    )
    op.create_index("ix_employer_postings_account_id", "employer_postings", ["account_id"])


def downgrade():
    op.drop_table("employer_postings")
    op.drop_table("account_oauth_identities")
    with op.batch_alter_table("accounts") as batch:
        batch.drop_column("role")
