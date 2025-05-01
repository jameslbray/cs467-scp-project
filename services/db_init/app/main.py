import logging
import time
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
import os

from config import get_settings
from models import Base, User, UserStatus

# Configure logging
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def wait_for_db(settings, max_retries=30, retry_interval=2):
    """Wait for the database to be available"""
    logger.info("Waiting for database to be available...")
    
    db_url = settings.DATABASE_URL
    retries = 0
    
    while retries < max_retries:
        try:
            # Try to connect to the database
            engine = create_engine(db_url)
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

def init_database():
    """Initialize the database with schemas and tables"""
    settings = get_settings()
    
    # Wait for database to be available
    if not wait_for_db(settings):
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
            
            logger.info("Creating extensions...")
            conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
            conn.execute(text('CREATE EXTENSION IF NOT EXISTS "pgcrypto"'))
        
        # Create tables
        logger.info("Creating tables...")
        Base.metadata.create_all(engine)
        
        # Grant permissions to app_user
        with engine.begin() as conn:
            logger.info("Granting permissions to app_user...")
            
            # Schema permissions
            conn.execute(text("GRANT USAGE ON SCHEMA users TO app_user"))
            conn.execute(text("GRANT USAGE ON SCHEMA presence TO app_user"))
            
            # Table permissions
            conn.execute(text("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA users TO app_user"))
            conn.execute(text("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA presence TO app_user"))
            
            # Sequence permissions
            conn.execute(text("GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA users TO app_user"))
            conn.execute(text("GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA presence TO app_user"))
            
            # Set search path for app_user
            conn.execute(text("ALTER ROLE app_user SET search_path TO users, presence, public"))
            
            # Allow app_user to create objects in these schemas
            conn.execute(text("GRANT CREATE ON SCHEMA users TO app_user"))
            conn.execute(text("GRANT CREATE ON SCHEMA presence TO app_user"))
        
        # Set up initial data
        logger.info("Seeding initial data...")
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        try:
            # Check if test user exists
            test_user = db.query(User).filter(User.username == "test_user").first()
            
            if not test_user:
                logger.info("Creating test user...")
                test_user = User(
                    username="test_user",
                    email="test@example.com",
                    hashed_password="$argon2id$v=19$m=65536,t=3,p=4$GUMIQSjF+L+XslaqVSql1A$YRxMqFsROQsIl0cZjA0zZp7oUZbE7UCqqnGqRgb6c7M",
                    profile_picture_url="https://example.com/test.jpg"
                )
                db.add(test_user)
                db.commit()
                db.refresh(test_user)
                
                logger.info("Creating test user status...")
                test_status = UserStatus(
                    user_id=test_user.id,
                    status="offline"
                )
                db.add(test_status)
                db.commit()
            else:
                logger.info(f"Test user already exists (id: {test_user.id})")
                
            logger.info("Database initialization completed successfully")
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