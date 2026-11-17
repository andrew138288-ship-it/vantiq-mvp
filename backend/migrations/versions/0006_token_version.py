"""Add token version for access-token revocation.

Revision ID: 0006_token_version
Revises: 0005_email_verification
"""
from alembic import op
import sqlalchemy as sa

revision = "0006_token_version"
down_revision = "0005_email_verification"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("users", "token_version")
