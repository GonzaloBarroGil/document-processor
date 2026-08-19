"""Add ownership and review fields to documents (W0.5).

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-19

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("documents", sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column(
        "documents",
        sa.Column("reviewed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "documents", sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.add_column("documents", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("documents", sa.Column("edited_fields", postgresql.JSONB(), nullable=True))
    op.create_foreign_key("documents_user_id_fkey", "documents", "users", ["user_id"], ["id"])
    op.create_foreign_key(
        "documents_reviewed_by_fkey", "documents", "users", ["reviewed_by"], ["id"]
    )
    op.create_index("idx_documents_user", "documents", ["user_id", "created_at"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("idx_documents_user", table_name="documents")
    op.drop_constraint("documents_reviewed_by_fkey", "documents", type_="foreignkey")
    op.drop_constraint("documents_user_id_fkey", "documents", type_="foreignkey")
    op.drop_column("documents", "edited_fields")
    op.drop_column("documents", "reviewed_at")
    op.drop_column("documents", "reviewed_by")
    op.drop_column("documents", "reviewed")
    op.drop_column("documents", "user_id")
