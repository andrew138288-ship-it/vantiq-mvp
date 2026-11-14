"""Track explicit user authorization before conversation context ingestion."""
from alembic import op
import sqlalchemy as sa

revision = "0003_context_authorization"
down_revision = "0002_user_password_hash"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("context_authorized_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("conversations", "context_authorized_at")
