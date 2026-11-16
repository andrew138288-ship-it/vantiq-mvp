"""Add explicit free-account lifecycle state.

Revision ID: 0007_account_status
Revises: 0006_token_version
"""
from alembic import op
import sqlalchemy as sa

revision = "0007_account_status"
down_revision = "0006_token_version"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("account_status", sa.String(length=32), nullable=False, server_default="free_active"),
    )


def downgrade() -> None:
    op.drop_column("users", "account_status")
