from datetime import datetime, timedelta, UTC
from typing import Optional, Union, Any
import uuid
import re
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from ..db.database import get_db
from ..db.models import User as DBUser, BlacklistedToken
from ..schemas import User, JWTTokenData, Token
from .config import get_settings

settings = get_settings()

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def verify_password(
    plain_password: str, hashed_password: str
) -> bool:
    """
    Verify a plain password against a hashed password.

    Args:
        plain_password: The plain text password to verify
        hashed_password: The hashed password to compare against

    Returns:
        True if passwords match, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(
    subject: Union[str, Any], expires_delta: Optional[timedelta] = None
) -> Token:
    """
    Create a new JWT access token.

    Args:
        subject: Subject to encode in the token (typically username)
        expires_delta: Optional expiration time delta

    Returns:
        Token object containing the JWT access token
    """
    to_encode = {"sub": subject}  # Set sub claim first
    now = datetime.now(UTC)

    # Set expiration time
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=15)

    # Create JWT token data
    token_id = str(uuid.uuid4())
    token_data = JWTTokenData(
        username=subject,
        exp=expire,
        iat=now,
        jti=token_id
    )

    # Convert to dict for JWT encoding
    to_encode.update(token_data.model_dump(exclude_none=True))

    # Encode the JWT
    secret_key = str(settings.JWT_SECRET_KEY.get_secret_value())
    encoded_jwt = jwt.encode(
        to_encode, secret_key, algorithm=settings.JWT_ALGORITHM
    )

    # Return Token model with access_token, token_type, and expires_at
    return Token(access_token=encoded_jwt, token_type="bearer", expires_at=expire)


def blacklist_token(
    token: str,
    db: Session,
    user_id: Optional[int] = None,
    username: Optional[str] = None,
) -> None:
    """
    Add a token to the blacklist in the database.

    Args:
        token: The JWT token to blacklist
        db: Database session
        user_id: Optional user ID associated with the token
        username: Optional username associated with the token
    """
    try:
        # Decode the token to get expiration time
        secret_key = settings.JWT_SECRET_KEY.get_secret_value()
        payload = jwt.decode(
            token, secret_key, algorithms=[settings.JWT_ALGORITHM]
        )
        exp_timestamp = payload.get("exp")

        if exp_timestamp:
            expires_at = datetime.fromtimestamp(exp_timestamp, tz=UTC)
        else:
            # Default expiration if not found in token
            expires_at = datetime.now(UTC) + timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )

        # Create blacklisted token record
        blacklisted_token = BlacklistedToken(
            token=token,
            user_id=user_id,
            username=username,
            blacklisted_at=datetime.now(UTC),
            expires_at=expires_at,
        )

        db.add(blacklisted_token)
        db.commit()

    except JWTError:
        # If token is invalid, still blacklist it with default expiration
        blacklisted_token = BlacklistedToken(
            token=token,
            user_id=user_id,
            username=username,
            blacklisted_at=datetime.now(UTC),
            expires_at=datetime.now(
                UTC) + timedelta(days=30),  # Default 30 days
        )

        db.add(blacklisted_token)
        db.commit()


def is_token_blacklisted(token: str, db: Session) -> bool:
    """
    Check if a token is blacklisted in the database.

    Args:
        token: The JWT token to check
        db: Database session

    Returns:
        bool: True if token is blacklisted, False otherwise
    """
    # Check if token exists in blacklist
    blacklisted = (
        db.query(BlacklistedToken).filter(
            BlacklistedToken.token == token).first()
    )

    return blacklisted is not None


def get_token_data(token: str, db: Session) -> JWTTokenData:
    """
    Decode and verify a JWT token, returning the token data if valid.

    Args:
        token: The JWT token to verify
        db: Database session

    Returns:
        JWTTokenData: The token data if valid

    Raises:
        HTTPException: If token is invalid or blacklisted
    """
    try:
        # Check if token is blacklisted
        if is_token_blacklisted(token, db):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )

        secret_key = settings.JWT_SECRET_KEY.get_secret_value()
        payload = jwt.decode(
            token, secret_key, algorithms=[settings.JWT_ALGORITHM]
        )

        # Try both 'sub' and 'username' claims
        username: str = payload.get("sub") or payload.get("username")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Parse JWT payload into JWTTokenData model
        token_data = JWTTokenData(
            username=username,
            exp=(
                datetime.fromtimestamp(payload.get("exp"))
                if payload.get("exp")
                else None
            ),
            iat=(
                datetime.fromtimestamp(payload.get("iat"))
                if payload.get("iat")
                else None
            ),
            jti=payload.get("jti"),
        )
        return token_data
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> User:
    """Get the current user from the JWT token in the request."""
    token_data = get_token_data(token, db)

    # Get user from database
    user = db.query(DBUser).filter(
        DBUser.username == token_data.username).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Use model_validate instead of from_orm (Pydantic v2 style)
    return User.model_validate(user, from_attributes=True)


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Check if the current user is active."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )
    return current_user


def validate_password_strength(password: str) -> bool:
    """
    Validate that a password meets minimum security requirements:
    - At least 8 characters long
    - Contains at least one uppercase letter
    - Contains at least one lowercase letter
    - Contains at least one number
    - Contains at least one special character
    """
    if len(password) < 8:
        return False

    if not re.search(r"[A-Z]", password):
        return False

    if not re.search(r"[a-z]", password):
        return False

    if not re.search(r"\d", password):
        return False

    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False

    return True
