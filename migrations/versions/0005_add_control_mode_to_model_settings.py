"""add control mode to model settings

Revision ID: 0005_control_mode_settings
Revises: 0004_add_mode_to_command_log
Create Date: 2026-05-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_control_mode_settings"
down_revision: Union[str, None] = "0004_add_mode_to_command_log"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "model_settings",
        sa.Column("control_mode", sa.String(length=20), server_default="mqtt", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("model_settings", "control_mode")
