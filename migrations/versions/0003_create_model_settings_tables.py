"""create model settings tables

Revision ID: 0003_model_settings
Revises: 419bf84c6126
Create Date: 2026-05-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0003_model_settings"
down_revision: Union[str, None] = "419bf84c6126"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "model_settings",
        sa.Column("id", postgresql.UUID(), autoincrement=False, nullable=False),
        sa.Column("selected_chat_model", sa.String(length=200), nullable=True),
        sa.Column("embedding_model", sa.String(length=200), nullable=True),
        sa.Column("embedding_dimension", sa.Integer(), nullable=True),
        sa.Column("last_refresh_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_refresh_error", sa.Text(), nullable=True),
        sa.Column("last_refresh_status", sa.String(length=50), nullable=True),
        sa.Column("selected_model_available", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="model_settings_pkey"),
    )
    op.create_table(
        "openrouter_model_catalog",
        sa.Column("id", postgresql.UUID(), autoincrement=False, nullable=False),
        sa.Column("model_id", sa.String(length=200), nullable=False),
        sa.Column("name", sa.String(length=255), autoincrement=False, nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=True),
        sa.Column("capability_flags", postgresql.JSONB(), nullable=True),
        sa.Column("prompt_price", sa.Integer(), nullable=True),
        sa.Column("completion_price", sa.Integer(), nullable=True),
        sa.Column("context_length", sa.Integer(), nullable=True),
        sa.Column("max_completion_tokens", sa.Integer(), nullable=True),
        sa.Column("raw_metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="openrouter_model_catalog_pkey"),
        sa.UniqueConstraint("model_id", name="openrouter_model_catalog_model_id_key"),
    )


def downgrade() -> None:
    op.drop_table("openrouter_model_catalog")
    op.drop_table("model_settings")
