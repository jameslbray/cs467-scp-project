import asyncio
import logging
import os
import time
from datetime import datetime, timedelta, UTC
from config import get_settings
from init_mongodb import init_mongodb
from models import Base, User, UserStatus, Connection, PasswordResetToken
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

# Configure logging
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def create_database():
    """Create the database schema"""
    settings = get_settings()
    postgres_url_parts = settings.DATABASE_URL.split("/")
    postgres_url = '/'.join(postgres_url_parts[:-1] + ['postgres'])

    logger.info("Checking if sycolibre database exists...")
    try:
        engine = create_engine(postgres_url)

        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 FROM pg_database WHERE datname = 'sycolibre'"))
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

def wait_for_db(max_retries: int=30, retry_interval: int=2):
    """Wait for the database to be available"""
    logger.info("Waiting for database to be available...")

    settings = get_settings()
    postgres_url = settings.DATABASE_URL
    retries = 0

    while retries < max_retries:
        try:
            # Try to connect to the database
            engine = create_engine(postgres_url)
            conn = engine.connect()
            conn.close()
            logger.info("Successfully connected to the database")
            return True
        except OperationalError as e:
            logger.warning(f"Database not available yet: {e}")
            retries += 1
            time.sleep(retry_interval)

    logger.error(f"Could not connect to database after {max_retries} attempts")
    return False

def create_roles():
    """Create roles for the database"""
    logger.info("Creating roles...")
    settings = get_settings()

    postgres_url = settings.DATABASE_URL

    # TODO: add this to env file
    postgres_users = [
        "Michael",
        "Nicholas",
        "James"
    ]
    try:
        engine = create_engine(postgres_url)
        with engine.connect() as conn:
            conn.execute(text("DROP TABLE IF EXISTS connections.connections CASCADE"))
            for user in postgres_users:
                result = conn.execute(text(f"SELECT 1 FROM pg_roles WHERE rolname = '{user}'"))
                exists = result.scalar() is not None

                if not exists:
                    logger.info(f"Creating database user '{user}'...")
                    # Create user with password - in production, use more secure passwords
                    conn.execute(text(f"CREATE USER {user} WITH PASSWORD 'password'"))
                else:
                    logger.info(f"Database user '{user}' already exists")

                logger.info(f"Granting permissions to {user}...")

                # Schema permissions
                conn.execute(text(f"GRANT USAGE ON SCHEMA users TO {user}"))
                conn.execute(text(f"GRANT USAGE ON SCHEMA presence TO {user}"))
                conn.execute(text(f"GRANT USAGE ON SCHEMA connections TO {user}"))

                # Table permissions
                conn.execute(text(f"GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA users TO {user}"))
                conn.execute(text(f"GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA presence TO {user}"))
                conn.execute(text(f"GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA connections TO {user}"))

                # Sequence permissions
                conn.execute(text(f"GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA users TO {user}"))
                conn.execute(text(f"GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA presence TO {user}"))
                conn.execute(text(f"GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA connections TO {user}"))

                # Set search path
                conn.execute(text(f"ALTER ROLE {user} SET search_path TO users, presence, connections, public"))

                # Allow user to create objects in these schemas
                conn.execute(text(f"GRANT CREATE ON SCHEMA users TO {user}"))
                conn.execute(text(f"GRANT CREATE ON SCHEMA presence TO {user}"))
                conn.execute(text(f"GRANT CREATE ON SCHEMA connections TO {user}"))

            # Grant future permissions for new tables/sequences
            conn.execute(text("ALTER DEFAULT PRIVILEGES IN SCHEMA users GRANT ALL ON TABLES TO " + ", ".join(postgres_users)))
            conn.execute(text("ALTER DEFAULT PRIVILEGES IN SCHEMA presence GRANT ALL ON TABLES TO " + ", ".join(postgres_users)))
            conn.execute(text("ALTER DEFAULT PRIVILEGES IN SCHEMA connections GRANT ALL ON TABLES TO " + ", ".join(postgres_users)))
            conn.execute(text("ALTER DEFAULT PRIVILEGES IN SCHEMA users GRANT ALL ON SEQUENCES TO " + ", ".join(postgres_users)))
            conn.execute(text("ALTER DEFAULT PRIVILEGES IN SCHEMA presence GRANT ALL ON SEQUENCES TO " + ", ".join(postgres_users)))
            conn.execute(text("ALTER DEFAULT PRIVILEGES IN SCHEMA connections GRANT ALL ON SEQUENCES TO " + ", ".join(postgres_users)))
    except OperationalError as e:
        logger.error(f"Error seeding data: {e}", exc_info=True)


def init_database():
    """Initialize the database with schemas and tables"""

    asyncio.run(init_mongodb())
    settings = get_settings()


    if not create_database():
        logger.error("Failed to create the database")
        return False

    # Wait for database to be available
    if not wait_for_db():
        logger.error("Database initialization failed: could not connect to database")
        return False

    logger.info("Starting database initialization")

    # Create engine
    engine = create_engine(settings.DATABASE_URL)

    try:
        # Create schemas
        with engine.begin() as conn:
            logger.info("Creating schemas...")
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS users"))
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS presence"))
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS connections"))

            logger.info("Creating extensions...")
            conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
            conn.execute(text('CREATE EXTENSION IF NOT EXISTS "pgcrypto"'))
            
            # These two lines are only needed if you update the models and want to reset the tables
            # logger.info("Dropping and recreating users table...")
            # conn.execute(text("DROP TABLE IF EXISTS users.users CASCADE"))
            
            # logger.info("Dropping and recreating connections table...")
            # conn.execute(text("DROP TABLE IF EXISTS connections.connections CASCADE"))
            
        
            with engine.begin() as conn:
                # Check if uuid-ossp extension is correctly loaded
                conn.execute(text("SELECT uuid_generate_v4()"))
                logger.info("UUID generation is working correctly")

        # Create tables
        logger.info("Creating tables...")
        Base.metadata.create_all(engine)

        # Set up initial data
        logger.info("Seeding initial data...")
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()

        try:
            # Check if test users exist
            test_user = db.query(User).filter(User.username == "test_user").first()
            test_user2 = db.query(User).filter(User.username == "test_user2").first()

            # Create first test user if needed
            if not test_user:
                logger.info("Creating test user 1...")
                test_user = User(
                    username="test_user",
                    email="test@example.com",
                    hashed_password="$argon2id$v=19$m=65536,t=3,p=4$GUMIQSjF+L+XslaqVSql1A$YRxMqFsROQsIl0cZjA0zZp7oUZbE7UCqqnGqRgb6c7M",
                    profile_picture_url="https://example.com/test.jpg"
                )
                db.add(test_user)
                db.commit()
                db.refresh(test_user)

                logger.info("Creating test user 1 status...")
                test_status = UserStatus(
                    user_id=test_user.id,
                    status="away"
                )
                db.add(test_status)
                db.commit()
                logger.info(f"Test user 1 added (id: {test_user.id})")
            else:
                logger.info(f"Test user 1 already exists (id: {test_user.id})")
            
            # Create second test user for connections
            if not test_user2:
                logger.info("Creating test user 2...")
                test_user2 = User(
                    username="test_user2",
                    email="test2@example.com",
                    hashed_password="$argon2id$v=19$m=65536,t=3,p=4$GUMIQSjF+L+XslaqVSql1A$YRxMqFsROQsIl0cZjA0zZp7oUZbE7UCqqnGqRgb6c7M",
                    profile_picture_url="https://example.com/test2.jpg"
                )
                db.add(test_user2)
                db.commit()
                db.refresh(test_user2)

                logger.info("Creating test user 2 status...")
                test_status2 = UserStatus(
                    user_id=test_user2.id,
                    status="online"
                )
                db.add(test_status2)
                db.commit()
                logger.info(f"Test user 2 added (id: {test_user2.id})")
            else:
                logger.info(f"Test user 2 already exists (id: {test_user2.id})")
            
            # Create connections between users (in both directions for bidirectional friendship)
            if test_user and test_user2:
                # Check if connections exist
                existing_connection1 = db.query(Connection).filter(
                    Connection.user_id == test_user.id,
                    Connection.friend_id == test_user2.id
                ).first()
                
                existing_connection2 = db.query(Connection).filter(
                    Connection.user_id == test_user2.id,
                    Connection.friend_id == test_user.id
                ).first()
                
                # Create first direction connection
                if not existing_connection1:
                    logger.info("Creating test connection (user1 -> user2)...")
                    test_connection1 = Connection(
                        user_id=test_user.id,
                        friend_id=test_user2.id,
                        status="accepted"
                    )
                    db.add(test_connection1)
                    db.commit()
                
                # Create second direction connection
                if not existing_connection2:
                    logger.info("Creating test connection (user2 -> user1)...")
                    test_connection2 = Connection(
                        user_id=test_user2.id,
                        friend_id=test_user.id,
                        status="accepted"
                    )
                    db.add(test_connection2)
                    db.commit()

            logger.info("Database initialization completed successfully")

            test_token = "test-reset-token-123"  # You can use secrets.token_urlsafe(32) for a real token
            expiry = datetime.now(UTC) + timedelta(hours=1)

            # Check if a test reset token already exists for this user
            existing_reset = db.query(PasswordResetToken).filter_by(user_id=test_user.id).first()
            if not existing_reset:
                logger.info("Creating test password reset token...")
                reset_entry = PasswordResetToken(
                    user_id=test_user.id,
                    token=test_token,
                    expires_at=expiry,
                )
                db.add(reset_entry)
                db.commit()
                db.refresh(reset_entry)
                logger.info(f"Test password reset token created: {test_token}")
            else:
                logger.info("Test password reset token already exists for test user")
            return True

        except Exception as e:
            logger.error(f"Error seeding data: {e}")
            db.rollback()
            return False
        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        return False

if __name__ == "__main__":
    if init_database():
        logger.info("Database initialization completed successfully")
    else:
        logger.error("Database initialization failed")
