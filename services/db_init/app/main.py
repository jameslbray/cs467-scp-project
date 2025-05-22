import asyncio

from sqlalchemy import create_engine

from services.db_init.app.config import get_settings
from services.db_init.app.db_utils.database import (
    create_database_if_not_exists,
    ensure_uuid_extension,
    wait_for_db,
)
from services.db_init.app.db_utils.logging_config import setup_logging
from services.db_init.app.db_utils.roles import create_roles_if_not_exist
from services.db_init.app.db_utils.schema import (
    create_schemas_if_not_exist,
    create_tables_if_not_exist,
    table_exists_and_has_data,
)
from services.db_init.app.db_utils.seed import seed_initial_data_if_not_exists
from services.db_init.app.init_mongodb import init_mongodb
from services.db_init.app.models import Base


def init_database() -> bool:
    """Initialize the database with schemas and tables, idempotently."""
    setup_logging()
    # Run the async MongoDB initialization
    asyncio.run(init_mongodb())
    settings = get_settings()
    if not create_database_if_not_exists():
        return False
    if not wait_for_db():
        return False
    engine = create_engine(settings.DATABASE_URL)
    # Only create schemas/tables if not already present with data
    if all(
        [
            table_exists_and_has_data(engine, "users", "users"),
            table_exists_and_has_data(engine, "presence", "presence"),
            table_exists_and_has_data(engine, "connections", "connections"),
        ]
    ):
        return True
    create_schemas_if_not_exist(engine)
    if not ensure_uuid_extension(engine):
        return False
    create_tables_if_not_exist(engine, Base)
    create_roles_if_not_exist(engine)
    if not seed_initial_data_if_not_exists(engine):
        return False
    return True


if __name__ == "__main__":
    if init_database():
        print("Database initialization completed successfully")
    else:
        print("Database initialization failed")
