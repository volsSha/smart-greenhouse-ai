"""create debug log table

Revision ID: 0001_create_debug_log
Revises:
Create Date: 2026-05-07
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_create_debug_log"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "debug_log",
        sa.Column("level", sa.String(length=20), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("component", sa.String(length=100), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("path", sa.String(length=500), nullable=True),
        sa.Column("method", sa.String(length=20), nullable=True),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Float(), nullable=True),
        sa.Column("request_id", sa.String(length=100), nullable=True),
        sa.Column("error_type", sa.String(length=200), nullable=True),
        sa.Column("stack_trace", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_debug_log_created_at", "debug_log", ["created_at"])
    op.create_index("ix_debug_log_level", "debug_log", ["level"])
    op.create_index("ix_debug_log_component", "debug_log", ["component"])


def downgrade() -> None:
    op.drop_index("ix_debug_log_component", table_name="debug_log")
    op.drop_index("ix_debug_log_level", table_name="debug_log")
    op.drop_index("ix_debug_log_created_at", table_name="debug_log")
    op.drop_table("debug_log")
