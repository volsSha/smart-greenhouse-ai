"""add zone source and mqtt credentials

Revision ID: 0006_zone_source_mqtt
Revises: 0005_control_mode_settings
Create Date: 2026-05-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006_zone_source_mqtt"
down_revision: Union[str, None] = "0005_control_mode_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "greenhouse_zones",
        sa.Column("source_type", sa.String(length=20), server_default="real", nullable=False),
    )
    op.add_column(
        "greenhouse_zones",
        sa.Column("simulator_managed", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column("edge_nodes", sa.Column("mqtt_username", sa.String(length=255), nullable=True))
    op.add_column("edge_nodes", sa.Column("mqtt_token", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("edge_nodes", "mqtt_token")
    op.drop_column("edge_nodes", "mqtt_username")
    op.drop_column("greenhouse_zones", "simulator_managed")
    op.drop_column("greenhouse_zones", "source_type")
