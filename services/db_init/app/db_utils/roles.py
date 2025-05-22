import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError

logger = logging.getLogger(__name__)


def create_roles_if_not_exist(engine: Engine) -> None:
    """Create roles/users and grant permissions if they do not exist."""
    postgres_users = ["Michael", "Nicholas", "James"]
    try:
        with engine.connect() as conn:
            for user in postgres_users:
                result = conn.execute(
                    text(f"SELECT 1 FROM pg_roles WHERE rolname = '{user}'")
                )
                exists = result.scalar() is not None
                if not exists:
                    logger.info(f"Creating database user '{user}'...")
                    conn.execute(
                        text(f"CREATE USER {user} WITH PASSWORD 'password'")
                    )
                else:
                    logger.info(f"Database user '{user}' already exists")
                logger.info(f"Granting permissions to {user}...")
                conn.execute(text(f"GRANT USAGE ON SCHEMA users TO {user}"))
                conn.execute(text(f"GRANT USAGE ON SCHEMA presence TO {user}"))
                conn.execute(
                    text(f"GRANT USAGE ON SCHEMA connections TO {user}")
                )
                conn.execute(
                    text(
                        f"GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA users TO {user}"
                    )
                )
                conn.execute(
                    text(
                        f"GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA presence TO {user}"
                    )
                )
                conn.execute(
                    text(
                        f"GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA connections TO {user}"
                    )
                )
                conn.execute(
                    text(
                        f"GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA users TO {user}"
                    )
                )
                conn.execute(
                    text(
                        f"GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA presence TO {user}"
                    )
                )
                conn.execute(
                    text(
                        f"GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA connections TO {user}"
                    )
                )
                conn.execute(
                    text(
                        f"ALTER ROLE {user} SET search_path TO users, presence, connections, public"
                    )
                )
                conn.execute(text(f"GRANT CREATE ON SCHEMA users TO {user}"))
                conn.execute(
                    text(f"GRANT CREATE ON SCHEMA presence TO {user}")
                )
                conn.execute(
                    text(f"GRANT CREATE ON SCHEMA connections TO {user}")
                )
            # Grant future permissions for new tables/sequences
            conn.execute(
                text(
                    "ALTER DEFAULT PRIVILEGES IN SCHEMA users GRANT ALL ON TABLES TO "
                    + ", ".join(postgres_users)
                )
            )
            conn.execute(
                text(
                    "ALTER DEFAULT PRIVILEGES IN SCHEMA presence GRANT ALL ON TABLES TO "
                    + ", ".join(postgres_users)
                )
            )
            conn.execute(
                text(
                    "ALTER DEFAULT PRIVILEGES IN SCHEMA connections GRANT ALL ON TABLES TO "
                    + ", ".join(postgres_users)
                )
            )
            conn.execute(
                text(
                    "ALTER DEFAULT PRIVILEGES IN SCHEMA users GRANT ALL ON SEQUENCES TO "
                    + ", ".join(postgres_users)
                )
            )
            conn.execute(
                text(
                    "ALTER DEFAULT PRIVILEGES IN SCHEMA presence GRANT ALL ON SEQUENCES TO "
                    + ", ".join(postgres_users)
                )
            )
            conn.execute(
                text(
                    "ALTER DEFAULT PRIVILEGES IN SCHEMA connections GRANT ALL ON SEQUENCES TO "
                    + ", ".join(postgres_users)
                )
            )
    except OperationalError as e:
        logger.error(f"Error creating roles: {e}", exc_info=True)
