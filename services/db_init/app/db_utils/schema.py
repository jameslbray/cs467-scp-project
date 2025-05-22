import logging

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeMeta

logger = logging.getLogger(__name__)


def create_schemas_if_not_exist(engine: Engine) -> None:
    """Create schemas if they do not exist."""
    with engine.begin() as conn:
        logger.info("Creating schemas if not exist...")
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS users"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS presence"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS connections"))


def create_tables_if_not_exist(engine: Engine, base: DeclarativeMeta) -> None:
    """Create tables if they do not exist."""
    logger.info("Creating tables if not exist...")
    base.metadata.create_all(engine)


def table_exists_and_has_data(engine: Engine, schema: str, table: str) -> bool:
    """Check if a table exists and has at least one row."""
    inspector = inspect(engine)
    if not inspector.has_table(table, schema=schema):
        return False
    with engine.connect() as conn:
        result = conn.execute(
            text(f'SELECT EXISTS (SELECT 1 FROM "{schema}"."{table}" LIMIT 1)')
        )
        return result.scalar() is True
