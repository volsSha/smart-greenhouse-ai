"""Alembic migration environment for async SQLAlchemy.

Uses the async engine from app.config and targets all models
registered in app.models so that autogenerate can detect schema changes.

This module is safe to import outside of Alembic (e.g. in tests) --
the actual migration logic only runs when invoked by the ``alembic`` CLI.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.models import Base  # noqa: F401  -- import all models so Alembic discovers them

# Metadata for autogenerate support -- always available for import
target_metadata = Base.metadata


def _configure() -> None:
    """Read alembic.ini, apply app settings overrides, and configure logging."""
    config = context.config

    # Interpret the config file for Python logging (if configured)
    if config.config_file_name is not None:
        fileConfig(config.config_file_name)

    # Override sqlalchemy.url from app config
    from app.config import get_settings

    settings = get_settings()
    config.set_main_option("sqlalchemy.url", settings.database.url.replace("%", "%%"))


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Generates SQL scripts without connecting to the database.
    """
    _configure()
    url = context.config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    """Run migrations using the provided connection."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode using an async engine."""
    _configure()
    config = context.config

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Entry point for online migrations -- delegates to async runner."""
    asyncio.run(run_async_migrations())


# This block only executes when invoked by the ``alembic`` command-line tool.
# It does NOT run on plain ``import migrations.env``.
if __name__ == "__main__" or hasattr(context, "config"):
    if context.is_offline_mode():
        run_migrations_offline()
    else:
        run_migrations_online()
