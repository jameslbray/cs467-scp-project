# fastAPI API Routers
import json
import logging
import os
import secrets
import sys
from datetime import UTC, datetime, timedelta

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
    status,
)
from fastapi.security import OAuth2PasswordRequestForm
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from services.users.app.core import security
from services.users.app.core.config import Settings, get_settings
from services.users.app.core.utils import (
    cleanup_expired_tokens,
    send_reset_email,
)
from services.users.app.db.database import get_db
from services.users.app.db.models import PasswordResetToken
from services.users.app.db.models import User as UserModel
from services.users.app.schemas import (
    PasswordResetConfirm,
    PasswordResetRequest,
    Token,
    UserCreate,
)
from services.users.app.schemas import UserSchema as User

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
    force=True,
)

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
logger = logging.getLogger(__name__)


router = APIRouter(tags=["users"])
settings = get_settings()


@router.get("/")
async def root():
    """Root endpoint that provides API information."""
    return {
        "service": "User Service API",
        "version": settings.VERSION,
        "description": settings.DESCRIPTION,
        "endpoints": {
            "register": "/register",
            "login": "/token",
            "logout": "/logout",
            "me": "/users/me",
            "health": "/health",
        },
    }


@router.get("/health")
async def health_check():
    """Health check endpoint for the service."""
    return {"status": "healthy"}


@router.post("/register", response_model=User)
async def register_user(
    user: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    rabbitmq_client = request.app.state.rabbitmq_client
    # Check if user already exists
    db_user = (
        db.query(UserModel)
        .filter(
            (UserModel.email == user.email)
            | (UserModel.username == user.username)
        )
        .first()
    )
    if db_user is not None:
        raise HTTPException(
            status_code=400, detail="Email or Username already registered"
        )

    # Validate password strength
    if not security.validate_password_strength(user.password):
        raise HTTPException(
            status_code=400,
            detail=(
                "Password must be at least 8 characters long and contain "
                "uppercase, lowercase, number, and special character"
            ),
        )

    # Create new user
    hashed_password = security.get_password_hash(user.password)
    db_user = UserModel(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # Publish user registration event
    await rabbitmq_client.publish_message(
        exchange="auth",
        routing_key="user.registered",
        message=json.dumps(
            {
                "user_id": str(db_user.id),
                "username": db_user.username,
                "email": db_user.email,
            }
        ),
    )

    # Get room ID for user
    room_id = await rabbitmq_client.publish_message(
        exchange="chat",
        routing_key="room.get_id_by_name",
        message=json.dumps({"name": "general"}),
    )

    if room_id:
        logger.info(f"Room ID for user {db_user.id}: {room_id}")
    else:
        logger.error(f"Failed to get room ID for user {db_user.id}")

    event = {
        "event": "add_user_to_room",
        "user_id": str(db_user.id),
        "room_id": room_id,
    }

    logger.info(f"Publishing event: {event}")

    await rabbitmq_client.publish_message(
        exchange="user",
        routing_key="user.add_to_room",
        message=json.dumps(event),
    )

    return db_user


@router.post("/token", response_model=Token)
@limiter.limit("5/minute")
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    rabbitmq_client = request.app.state.rabbitmq_client
    user = (
        db.query(UserModel)
        .filter(UserModel.username == form_data.username)
        .first()
    )
    if not user or not security.verify_password(
        form_data.password, str(user.hashed_password)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    access_token = security.create_access_token(
        user_id=user.id, expires_delta=access_token_expires
    )

    # Publish user login event
    await rabbitmq_client.publish_message(
        exchange="auth",
        routing_key="user.login",
        message=json.dumps(
            {"user_id": str(user.id), "username": user.username}
        ),
    )

    # Publish presence update
    await rabbitmq_client.publish_message(
        exchange="user",
        routing_key=f"status.{user.id}",
        message=json.dumps(
            {
                "type": "status_update",
                "user_id": str(user.id),
                "status": "online",
                "last_changed": datetime.now().timestamp(),
            }
        ),
    )

    # 1. Get the General room ID via RPC
    response = await rabbitmq_client.rabbitmq_client.publish_and_wait(
        exchange="chat",
        routing_key="room.get_id_by_name",
        message={"action": "get_room_id_by_name", "name": "General"},
    )
    room_id = response.get("room_id")
    if room_id:
        # 2. Check if user is already a member
        is_member_response = (
            await rabbitmq_client.rabbitmq_client.publish_and_wait(
                exchange="chat",
                routing_key="room.is_user_member",
                message={
                    "action": "is_user_member",
                    "room_id": room_id,
                    "user_id": str(user.id),
                },
            )
        )
        if not is_member_response.get("is_member"):
            # 3. Add user to General room
            event = {
                "event": "add_user_to_room",
                "user_id": str(user.id),
                "room_id": room_id,
            }
            logger.info(
                f"Adding user {user.id} to General room {room_id} on login."
            )
            await rabbitmq_client.publish_message(
                exchange="user",
                routing_key="user.add_to_room",
                message=json.dumps(event),
            )
    else:
        logger.error(
            f"Could not get General room ID on login for user {user.id}."
        )

    return access_token


@router.get("/users/me", response_model=User)
async def read_users_me(
    current_user: User = Depends(security.get_current_user),
):
    return current_user


@router.post("/logout")
async def logout(
    request: Request,
    current_user: UserModel = Depends(security.get_current_user),
    token: str = Depends(security.oauth2_scheme),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    rabbitmq_client = request.app.state.rabbitmq_client
    """Logout the current user by blacklisting their token."""
    security.blacklist_token(
        token=token,
        db=db,
        user_id=current_user.id,
        username=current_user.username,
    )

    # Schedule cleanup of expired tokens
    background_tasks.add_task(cleanup_expired_tokens, db)

    # Publish user logout event
    await rabbitmq_client.publish_message(
        exchange="auth",
        routing_key="user.logout",
        message=json.dumps(
            {
                "user_id": str(current_user.id),
                "username": current_user.username,
            }
        ),
    )

    # Publish presence update
    await rabbitmq_client.publish_message(
        exchange="user",
        routing_key=f"status.{current_user.id}",
        message=json.dumps(
            {
                "type": "status_update",
                "user_id": str(current_user.id),
                "status": "offline",
                "last_changed": datetime.now().timestamp(),
            }
        ),
    )

    return {"message": "Successfully logged out"}


@router.post("/password-reset/")
async def password_reset(
    data: PasswordResetRequest, db: Session = Depends(get_db)
):
    user = db.query(UserModel).filter(UserModel.email == data.email).first()
    if user:
        # Generate a secure token
        token = secrets.token_urlsafe(32)
        expiry = datetime.now(UTC) + timedelta(hours=1)
        # Store token, user_id, expiry in a password_resets table (implement this model/table)
        reset_entry = PasswordResetToken(
            user_id=user.id,
            token=token,
            expires_at=expiry,
        )
        db.add(reset_entry)
        db.commit()
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
        send_reset_email(user.email, reset_url)
    return {
        "message": "If your email is registered, you will receive a reset link."
    }


@router.post("/password-reset-confirm/")
async def password_reset_confirm(
    data: PasswordResetConfirm, db: Session = Depends(get_db)
):
    # 1. Find the token
    reset_token = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token == data.token)
        .first()
    )
    expires_at = reset_token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if not reset_token or expires_at < datetime.now(UTC):
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    # 2. Get the user
    user = (
        db.query(UserModel).filter(UserModel.id == reset_token.user_id).first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 3. Validate new password (reuse your existing password validation)
    if not security.validate_password_strength(data.new_password):
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters long and contain uppercase, lowercase, number, and special character",
        )

    # 4. Update password
    user.hashed_password = security.get_password_hash(data.new_password)
    db.delete(reset_token)  # Invalidate the token
    db.commit()
    return {"message": "Password has been reset successfully."}


__all__ = ["router"]
