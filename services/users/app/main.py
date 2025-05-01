from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    status,
    Request,
    BackgroundTasks
)
from typing import cast
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import timedelta, datetime
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ExceptionHandler
import json
import logging
import sys
import os

from services.db_init.app.models import User as UserModel, BlacklistedToken
from .db.database import get_db
from .schemas import User, UserCreate, Token
from .core import security
from .core.rabbitmq import UserRabbitMQClient
from .core.config import Settings, get_settings

# Configure logging
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stdout,
    force=True
)

# Get logger for this file
logger = logging.getLogger(__name__)


# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])

# Get settings
settings = get_settings()
logger.info("Application settings loaded")

# Security headers middleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        return response


# Create FastAPI application
app = FastAPI(
    title="User Service API",
    description="Service for managing user authentication and profiles",
    version="0.1.0",
)
app.add_middleware(SlowAPIMiddleware)
app.state.limiter = limiter

app.add_exception_handler(RateLimitExceeded, cast(ExceptionHandler, _rate_limit_exceeded_handler))

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_CREDENTIALS,
    allow_methods=settings.CORS_METHODS,
    allow_headers=settings.CORS_HEADERS,
)


# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Initialize RabbitMQ client
rabbitmq_client = UserRabbitMQClient(settings=settings)


@app.post("/register", response_model=User)
async def register_user(
    user: UserCreate,
    db: Session = Depends(get_db)
):
    # Check if user already exists
    db_user = (
        db.query(UserModel)
        .filter(
            (UserModel.email == user.email) |
            (UserModel.username == user.username)
        )
        .first()
    )
    if db_user:
        raise HTTPException(
            status_code=400,
            detail="Email or Username already registered"
        )

    # Validate password strength
    if not security.validate_password_strength(user.password):
        raise HTTPException(
            status_code=400,
            detail=(
                "Password must be at least 8 characters long and contain "
                "uppercase, lowercase, number, and special character"
            )
        )

    # Create new user
    hashed_password = security.get_password_hash(user.password)
    db_user = UserModel(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # Publish user registration event
    await rabbitmq_client.publish_message(
        exchange="auth",
        routing_key="user.registered",
        message=json.dumps({
            "user_id": str(db_user.id),
            "username": db_user.username,
            "email": db_user.email
        })
    )

    return db_user


@app.post("/token", response_model=Token)
@limiter.limit("5/minute")
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    user = (
        db.query(UserModel)
        .filter(UserModel.username == form_data.username)
        .first()
    )
    if not user or not security.verify_password(
        form_data.password,
        str(user.hashed_password)
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
        subject=user.username,
        expires_delta=access_token_expires
    )

    # Publish user login event
    await rabbitmq_client.publish_message(
        exchange="auth",
        routing_key="user.login",
        message=json.dumps({
            "user_id": str(user.id),
            "username": user.username
        })
    )

    # Publish presence update
    await rabbitmq_client.publish_message(
        exchange="user_events",
        routing_key=f"status.{user.id}",
        message=json.dumps({
            "type": "status_update",
            "user_id": str(user.id),
            "status": "online",
            "last_changed": datetime.now().timestamp()
        })
    )

    return access_token


@app.get("/users/me", response_model=User)
async def read_users_me(
    current_user: User = Depends(security.get_current_user)
):
    return current_user


@app.get("/")
async def root():
    """Root endpoint that provides API information."""
    return {
        "service": "User Service API",
        "version": app.version,
        "description": app.description,
        "docs_url": "/docs",
        "endpoints": {
            "register": "/register",
            "login": "/token",
            "logout": "/logout",
            "me": "/users/me",
            "health": "/health"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for the service."""
    return {"status": "healthy"}


def cleanup_expired_tokens(db: Session):
    """Remove expired tokens from the blacklist."""
    now = datetime.utcnow()
    expired_tokens = (
        db.query(BlacklistedToken)
        .filter(BlacklistedToken.expires_at < now)
        .all()
    )

    for token in expired_tokens:
        db.delete(token)

    db.commit()
    return len(expired_tokens)


@app.post("/logout")
async def logout(
    current_user: User = Depends(security.get_current_user),
    token: str = Depends(security.oauth2_scheme),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """Logout the current user by blacklisting their token."""
    security.blacklist_token(
        token=token,
        db=db,
        user_id=current_user.id,
        username=current_user.username
    )

    # Schedule cleanup of expired tokens
    background_tasks.add_task(cleanup_expired_tokens, db)

    # Publish user logout event
    await rabbitmq_client.publish_message(
        exchange="auth",
        routing_key="user.logout",
        message=json.dumps({
            "user_id": current_user.id,
            "username": current_user.username
        })
    )

    # Publish presence update
    await rabbitmq_client.publish_message(
        exchange="user_events",
        routing_key=f"status.{current_user.id}",
        message=json.dumps({
            "type": "status_update",
            "user_id": current_user.id,
            "status": "offline",
            "last_changed": datetime.now().timestamp()
        })
    )

    return {"message": "Successfully logged out"}


@app.on_event("startup")
async def startup():
    """Initialize services and connections"""
    await rabbitmq_client.connect()


@app.on_event("shutdown")
async def shutdown():
    """Cleanup resources on shutdown"""
    await rabbitmq_client.close()
