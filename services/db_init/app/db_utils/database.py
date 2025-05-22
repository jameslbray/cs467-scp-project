import logging

from config import get_settings
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError

logger = logging.getLogger(__name__)


def create_database_if_not_exists() -> bool:
    """Create the database if it does not exist."""
    settings = get_settings()
    postgres_url_parts = settings.DATABASE_URL.split("/")
    postgres_url = "/".join(postgres_url_parts[:-1] + ["postgres"])
    try:
        engine = create_engine(postgres_url)
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = 'sycolibre'")
            )
            exists = result.scalar() is not None
            if not exists:
                logger.info("Database 'sycolibre' does not exist. Creating...")
                conn.execute(text("COMMIT"))
                conn.execute(text("CREATE DATABASE sycolibre"))
                logger.info("Database 'sycolibre' created successfully")
            else:
                logger.info("Database 'sycolibre' already exists")
        return True
    except Exception as e:
        logger.error(f"Error creating database: {e}")
        return False


def wait_for_db(max_retries: int = 30, retry_interval: int = 2) -> bool:
    """Wait for the database to be available."""
    logger.info("Waiting for database to be available...")
    settings = get_settings()
    postgres_url = settings.DATABASE_URL
    retries = 0
    while retries < max_retries:
        try:
            engine = create_engine(postgres_url)
            conn = engine.connect()
            conn.close()
            logger.info("Successfully connected to the database")
            return True
        except OperationalError as e:
            logger.warning(f"Database not available yet: {e}")
            retries += 1
            import time

            time.sleep(retry_interval)
    logger.error(f"Could not connect to database after {max_retries} attempts")
    return False


def ensure_uuid_extension(engine: Engine) -> bool:
    """Ensure the uuid-ossp extension exists in the current database."""
    try:
        with engine.begin() as conn:
            conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
            conn.execute(text("SELECT uuid_generate_v4()"))
        logger.info(
            "uuid-ossp extension is enabled and uuid_generate_v4() is available."
        )
        return True
    except Exception as e:
        logger.error(f"Failed to create or verify uuid-ossp extension: {e}")
        return False
