from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    status,
    Request,
    BackgroundTasks
)
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import timedelta, datetime
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

from .db import models, database
from .schemas import User, UserCreate, Token
from .core import security
from .core.rabbitmq import UserRabbitMQClient
from .core.config import Settings, get_settings

# Create database tables
models.Base.metadata.create_all(bind=database.engine)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

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

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins during development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiter to the app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Initialize RabbitMQ client
rabbitmq_client = UserRabbitMQClient()


@app.post("/register", response_model=User)
async def register_user(user: UserCreate, db: Session = Depends(database.get_db)):
    # Check if user already exists
    db_user = (
        db.query(models.User)
        .filter(
            (models.User.email == user.email) | (
                models.User.username == user.username)
        )
        .first()
    )
    if db_user:
        raise HTTPException(
            status_code=400, detail="Email or Username already registered"
        )

    # Validate password strength
    if not security.validate_password_strength(user.password):
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters long and contain uppercase, lowercase, number, and special character",
        )

    # Create new user
    hashed_password = security.get_password_hash(user.password)
    db_user = models.User(
        email=user.email, username=user.username, hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # Publish user registration event
    await rabbitmq_client.publish_user_event(
        "user_registered",
        {"user_id": db_user.id, "username": db_user.username, "email": db_user.email},
    )

    return db_user


@app.post("/token", response_model=Token)
@limiter.limit("5/minute")
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(database.get_db),
    settings: Settings = Depends(get_settings),
):
    user = (
        db.query(models.User).filter(
            models.User.username == form_data.username).first()
    )
    if not user or not security.verify_password(
        form_data.password, user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        subject=user.username, expires_delta=access_token_expires
    )

    # Publish user login event
    await rabbitmq_client.publish_user_event(
        "user_logged_in", {"user_id": user.id, "username": user.username}
    )

    return access_token


@app.get("/users/me", response_model=User)
async def read_users_me(current_user: User = Depends(security.get_current_user)):
    return current_user


@app.get("/")
async def root():
    """Serve the registration page."""
    return FileResponse("app/static/index.html")


@app.get("/health")
async def health_check():
    """Health check endpoint for the service."""
    return {"status": "healthy"}


def cleanup_expired_tokens(db: Session):
    """Remove expired tokens from the blacklist."""
    now = datetime.utcnow()
    expired_tokens = (
        db.query(models.BlacklistedToken)
        .filter(models.BlacklistedToken.expires_at < now)
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
    db: Session = Depends(database.get_db),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """Logout the current user by blacklisting their token."""
    security.blacklist_token(
        token=token, db=db, user_id=current_user.id, username=current_user.username
    )

    # Schedule cleanup of expired tokens
    background_tasks.add_task(cleanup_expired_tokens, db)

    # Publish user logout event
    await rabbitmq_client.publish_user_event(
        "user_logged_out",
        {"user_id": current_user.id, "username": current_user.username},
    )

    return {"message": "Successfully logged out"}


@app.on_event("startup")
async def startup():
    """Initialize services and connections"""
    await rabbitmq_client.initialize()


@app.on_event("shutdown")
async def shutdown():
    """Cleanup resources on shutdown"""
    await rabbitmq_client.close()
