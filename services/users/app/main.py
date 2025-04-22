from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import List

from .db import models, database
from .schemas import User, UserCreate, Token
from .core import security
from .core.rabbitmq import UserRabbitMQClient

# Create database tables
models.Base.metadata.create_all(bind=database.engine)

# Create FastAPI application
app = FastAPI(
    title="User Service API",
    description="Service for managing user authentication and profiles",
    version="0.1.0",
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Initialize RabbitMQ client
rabbitmq_client = UserRabbitMQClient()


@app.post("/register", response_model=User)
async def register_user(user: UserCreate, db: Session = Depends(database.get_db)):
    # Check if user already exists
    db_user = db.query(models.User).filter(
        (models.User.email == user.email) |
        (models.User.username == user.username)
    ).first()
    if db_user:
        raise HTTPException(
            status_code=400,
            detail="Email or username already registered"
        )

    # Create new user
    hashed_password = security.get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # Publish user registration event
    await rabbitmq_client.publish_user_event(
        "user_registered",
        {
            "user_id": db_user.id,
            "username": db_user.username,
            "email": db_user.email
        }
    )

    return db_user


@app.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(database.get_db)
):
    user = db.query(models.User).filter(
        models.User.username == form_data.username).first()
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(
        minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    # Publish user login event
    await rabbitmq_client.publish_user_event(
        "user_logged_in",
        {
            "user_id": user.id,
            "username": user.username
        }
    )

    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/users/me", response_model=User)
async def read_users_me(
    current_user: User = Depends(security.get_current_user)
):
    return current_user


@app.get("/")
async def root():
    """Serve the registration page."""
    return FileResponse("app/static/index.html")


@app.get("/health")
async def health_check():
    """Health check endpoint for the service."""
    return {"status": "healthy"}


@app.on_event("startup")
async def startup():
    """Initialize services and connections"""
    await rabbitmq_client.initialize()


@app.on_event("shutdown")
async def shutdown():
    """Cleanup resources on shutdown"""
    await rabbitmq_client.close()
