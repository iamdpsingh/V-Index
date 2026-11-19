"""Index due-source scheduling and active job lookup."""

from alembic import op

revision = "e8f36d47b501"
down_revision = "ce19f07ae2c1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index("ix_sources_next_check", "sources", ["next_check"])
    op.create_index("ix_observations_status_job", "observations", ["status", "job_id"])


def downgrade():
    op.drop_index("ix_observations_status_job", table_name="observations")
    op.drop_index("ix_sources_next_check", table_name="sources")
