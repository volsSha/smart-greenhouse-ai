"""add plant batch profile link

Revision ID: 0007_plant_batch_profile
Revises: 0006_zone_source_mqtt
Create Date: 2026-05-20
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007_plant_batch_profile"
down_revision: Union[str, None] = "0006_zone_source_mqtt"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("plant_batches", sa.Column("profile_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_plant_batches_profile_id_plant_profiles",
        "plant_batches",
        "plant_profiles",
        ["profile_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_plant_batches_profile_id", "plant_batches", ["profile_id"])


def downgrade() -> None:
    op.drop_index("ix_plant_batches_profile_id", table_name="plant_batches")
    op.drop_constraint(
        "fk_plant_batches_profile_id_plant_profiles",
        "plant_batches",
        type_="foreignkey",
    )
    op.drop_column("plant_batches", "profile_id")
