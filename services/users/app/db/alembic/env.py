from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from shared.db.base import metadata

config = context.config
fileConfig(config.config_file_name)


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=metadata,  # point to shared metadata
            compare_type=True,  # detect type changes
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    context.run_migrations()
else:
    run_migrations_online()
