"""Add email verification for free accounts.

Revision ID: 0005_email_verification
Revises: 0004_password_reset_tokens
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005_email_verification"
down_revision = "0004_password_reset_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing accounts remain usable; newly registered users explicitly start unverified.
    op.add_column(
        "users",
        sa.Column("is_email_verified", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "email_verification_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(length=64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_email_verification_tokens_user_id",
        "email_verification_tokens",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_email_verification_tokens_user_id", table_name="email_verification_tokens")
    op.drop_table("email_verification_tokens")
    op.drop_column("users", "is_email_verified")
