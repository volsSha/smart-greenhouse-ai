"""Tests for Alembic migration setup and model metadata.

These tests verify the migration configuration is correct and that all
expected tables are present in the model metadata, without requiring a
running PostgreSQL instance.
"""

import pytest

from app.models import Base, GreenhouseGroup


# ---------------------------------------------------------------------------
# Table existence tests (metadata-based, no DB needed)
# ---------------------------------------------------------------------------

EXPECTED_TABLES = {
    "greenhouse_groups",
    "greenhouses",
    "greenhouse_zones",
    "edge_nodes",
    "sensor_registry",
    "actuator_registry",
    "plant_batches",
    "plant_profiles",
    "group_control_policies",
    "control_setpoints",
    "command_log",
    "alert_log",
    "ai_conversations",
    "ai_messages",
    "ai_tool_calls",
    "rag_documents",
    "rag_chunks",
}


class TestModelMetadata:
    """Verify that all tables from DATABASE.md are registered in SQLAlchemy metadata."""

    def test_all_tables_present(self):
        """Every table defined in the schema doc must appear in Base.metadata."""
        actual = set(Base.metadata.tables.keys())
        missing = EXPECTED_TABLES - actual
        extra = actual - EXPECTED_TABLES
        assert not missing, f"Missing tables: {missing}"
        assert not extra, f"Unexpected tables: {extra}"

    @pytest.mark.parametrize("table_name", EXPECTED_TABLES)
    def test_table_has_uuid_primary_key(self, table_name: str):
        """Every table must have a UUID primary key column named 'id'."""
        table = Base.metadata.tables[table_name]
        pk_columns = [c for c in table.columns if c.primary_key]
        assert len(pk_columns) == 1, f"{table_name}: expected 1 PK column, got {len(pk_columns)}"
        pk = pk_columns[0]
        assert pk.name == "id", f"{table_name}: PK column should be 'id', got '{pk.name}'"

    def test_greenhouse_groups_columns(self):
        """Verify greenhouse_groups has the exact expected columns."""
        table = Base.metadata.tables["greenhouse_groups"]
        col_names = {c.name for c in table.columns}
        assert col_names == {"id", "name", "location", "description", "created_at"}

    def test_greenhouses_columns(self):
        """Verify greenhouses columns and group_id foreign key."""
        table = Base.metadata.tables["greenhouses"]
        col_names = {c.name for c in table.columns}
        assert col_names == {"id", "group_id", "name", "location", "description", "created_at"}
        fk_names = {fk.target_fullname for fk in table.foreign_keys}
        assert "greenhouse_groups.id" in fk_names

    def test_rag_chunks_has_vector_column(self):
        """Verify rag_chunks has an embedding vector column."""
        table = Base.metadata.tables["rag_chunks"]
        assert "embedding" in {c.name for c in table.columns}


# ---------------------------------------------------------------------------
# Mixin verification (via actual model that uses the mixin)
# ---------------------------------------------------------------------------

class TestMixins:
    """Verify that mixins correctly contribute columns to model tables."""

    def test_id_timestamp_mixin_contributes_id_and_created_at(self):
        """GreenhouseGroup uses IdTimestampMixin and should have id + created_at."""
        table = Base.metadata.tables["greenhouse_groups"]
        col_names = {c.name for c in table.columns}
        assert "id" in col_names
        assert "created_at" in col_names

    def test_id_only_mixin_contributes_id(self):
        """PlantProfile uses IdMixin only (no created_at)."""
        table = Base.metadata.tables["plant_profiles"]
        col_names = {c.name for c in table.columns}
        assert "id" in col_names
        assert "created_at" not in col_names


# ---------------------------------------------------------------------------
# Alembic env.py import test
# ---------------------------------------------------------------------------

class TestAlembicEnv:
    """Verify that migrations/env.py can be imported and configured."""

    def test_env_module_importable(self):
        """migrations.env should import without errors."""
        import migrations.env  # noqa: F401

    def test_env_targets_base_metadata(self):
        """The env module should use Base.metadata as target_metadata."""
        from migrations.env import target_metadata

        assert target_metadata is Base.metadata


# ---------------------------------------------------------------------------
# Alembic configuration test
# ---------------------------------------------------------------------------

class TestAlembicConfig:
    """Verify alembic.ini and env.py integration."""

    def test_alembic_ini_exists(self):
        """alembic.ini must exist at project root."""
        import os

        assert os.path.exists("alembic.ini"), "alembic.ini not found"

    def test_script_location_is_migrations(self):
        """alembic.ini should point script_location to 'migrations'."""
        from alembic.config import Config

        cfg = Config("alembic.ini")
        assert cfg.get_main_option("script_location") == "migrations"
