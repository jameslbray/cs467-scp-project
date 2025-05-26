import json
import logging
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from services.db_init.app.models import (
    Connection,
    PasswordResetToken,
    User,
    UserStatus,
)

logger = logging.getLogger(__name__)

ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
)


def seed_initial_data_if_not_exists(engine: Engine) -> bool:
    """Seed initial data if it does not already exist."""
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        # Use hardcoded UUIDs for test users
        TEST_USER1_ID = "11111111-1111-1111-1111-111111111111"
        TEST_USER2_ID = "22222222-2222-2222-2222-222222222222"
        test_user = db.query(User).filter(User.username == "test_user").first()
        test_user2 = (
            db.query(User).filter(User.username == "test_user2").first()
        )
        if not test_user:
            logger.info("Creating test user 1...")
            test_user = User(
                id=TEST_USER1_ID,
                username="test_user",
                email="test@example.com",
                hashed_password=ph.hash("password"),
                profile_picture_url="https://example.com/test.jpg",
            )
            db.add(test_user)
            db.commit()
            db.refresh(test_user)
            logger.info("Creating test user 1 status...")
            test_status = UserStatus(user_id=test_user.id, status="away")
            db.add(test_status)
            db.commit()
            logger.info(f"Test user 1 added (id: {test_user.id})")
        else:
            logger.info(f"Test user 1 already exists (id: {test_user.id})")
        if not test_user2:
            logger.info("Creating test user 2...")
            test_user2 = User(
                id=TEST_USER2_ID,
                username="test_user2",
                email="test2@example.com",
                hashed_password=ph.hash("password"),
                profile_picture_url="https://example.com/test2.jpg",
            )
            db.add(test_user2)
            db.commit()
            db.refresh(test_user2)
            logger.info("Creating test user 2 status...")
            test_status2 = UserStatus(user_id=test_user2.id, status="online")
            db.add(test_status2)
            db.commit()
            logger.info(f"Test user 2 added (id: {test_user2.id})")
        else:
            logger.info(f"Test user 2 already exists (id: {test_user2.id})")
        if test_user and test_user2:
            existing_connection1 = (
                db.query(Connection)
                .filter(
                    Connection.user_id == test_user.id,
                    Connection.friend_id == test_user2.id,
                )
                .first()
            )
            existing_connection2 = (
                db.query(Connection)
                .filter(
                    Connection.user_id == test_user2.id,
                    Connection.friend_id == test_user.id,
                )
                .first()
            )
            if not existing_connection1:
                logger.info("Creating test connection (user1 -> user2)...")
                test_connection1 = Connection(
                    user_id=test_user.id,
                    friend_id=test_user2.id,
                    status="accepted",
                )
                db.add(test_connection1)
                db.commit()
            if not existing_connection2:
                logger.info("Creating test connection (user2 -> user1)...")
                test_connection2 = Connection(
                    user_id=test_user2.id,
                    friend_id=test_user.id,
                    status="accepted",
                )
                db.add(test_connection2)
                db.commit()
            # Write test user IDs and usernames to a shared file for MongoDB seeding
            test_users = [
                {"id": TEST_USER1_ID, "username": "test_user"},
                {"id": TEST_USER2_ID, "username": "test_user2"},
            ]
            with open("/tmp/test_users.json", "w") as f:
                json.dump(test_users, f)
        test_token = "test-reset-token-123"
        expiry = datetime.now(UTC) + timedelta(hours=1)
        existing_reset = (
            db.query(PasswordResetToken)
            .filter_by(user_id=test_user.id)
            .first()
        )
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
            logger.info(
                "Test password reset token already exists for test user"
            )
        return True
    except Exception as e:
        logger.error(f"Error seeding data: {e}", exc_info=True)
        db.rollback()
        return False
    finally:
        db.close()
