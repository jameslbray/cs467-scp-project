# services/users/app/db/models.py
from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    profile_picture_url = Column(String(255))
    last_login = Column(DateTime)

    # one‑to‑one relationship to UserStatus
    status = relationship(
        "UserStatus",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # Relationship to blacklisted tokens
    blacklisted_tokens = relationship("BlacklistedToken", back_populates="user")


class UserStatus(Base):
    __tablename__ = "user_status"
    __table_args__ = (
        CheckConstraint(
            "status IN ('online', 'away', 'offline')",
            name="ck_user_status_enum",
        ),
        {
            "comment": (
                "Stores the current online status of users "
                "and when it was last updated"
            )
        },
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    status = Column(
        String(10),
        nullable=False,
        server_default="'offline'",
    )
    last_status_change = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    user = relationship("User", back_populates="status")


class BlacklistedToken(Base):
    __tablename__ = "blacklisted_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    username = Column(String)
    blacklisted_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)

    # Relationship to user (optional)
    user = relationship("User", back_populates="blacklisted_tokens")
