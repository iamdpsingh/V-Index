"""Remove derived resume text while preserving encrypted files."""

import sqlalchemy as sa
from alembic import op

revision = "ce19f07ae2c1"
down_revision = "b6a6ec9a8083"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("account_resumes") as batch:
        batch.drop_column("text_ciphertext")
        batch.drop_column("text_characters")


def downgrade():
    # Derived text cannot be recovered by a schema rollback.
    with op.batch_alter_table("account_resumes") as batch:
        batch.add_column(sa.Column("text_ciphertext", sa.LargeBinary(), nullable=True))
        batch.add_column(sa.Column("text_characters", sa.Integer(), server_default="0", nullable=False))
