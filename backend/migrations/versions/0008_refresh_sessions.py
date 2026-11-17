"""Add rotating refresh sessions.

Revision ID: 0008_refresh_sessions
Revises: 0007_account_status
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0008_refresh_sessions"
down_revision = "0007_account_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "refresh_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("family_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False, unique=True),
        sa.Column("user_agent", sa.String(length=300), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_refresh_sessions_user_id", "refresh_sessions", ["user_id"])
    op.create_index("ix_refresh_sessions_user_session", "refresh_sessions", ["user_id", "session_id"])
    op.create_index("ix_refresh_sessions_family", "refresh_sessions", ["family_id"])
    op.alter_column("users", "token_version", server_default="0")


def downgrade() -> None:
    op.drop_index("ix_refresh_sessions_family", table_name="refresh_sessions")
    op.drop_index("ix_refresh_sessions_user_session", table_name="refresh_sessions")
    op.drop_index("ix_refresh_sessions_user_id", table_name="refresh_sessions")
    op.drop_table("refresh_sessions")
