"""Store a private, encrypted profile photo."""

import sqlalchemy as sa
from alembic import op

revision = "c1f43ed058e0"
down_revision = "e1aa300f9982"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("account_profiles", sa.Column("photo_ciphertext", sa.LargeBinary()))


def downgrade() -> None:
    with op.batch_alter_table("account_profiles") as batch:
        batch.drop_column("photo_ciphertext")
