"""add mode column to command_log

Revision ID: 0004_add_mode_to_command_log
Revises: 0003_model_settings
Create Date: 2026-05-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_add_mode_to_command_log"
down_revision: Union[str, None] = "0003_model_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "command_log",
        sa.Column("mode", sa.String(length=20), server_default="mqtt", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("command_log", "mode")
