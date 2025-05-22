# services/users/app/db/models.py
from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Index, relationship

from services.connections.app.db.models import (
    Connection,  # noqa: F401, SQL alchemy just needs to know about the model
)
from services.shared.base import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        {"schema": "users"},
        Index("idx_username", "username"),
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
    )
    username = Column(String(50), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    profile_picture_url = Column(String(255))
    last_login = Column(DateTime)

    # one‑to‑one relationship to UserStatus
    status = relationship(
        "UserStatus",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    connections = relationship(
        "Connection",
        foreign_keys="Connection.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    friends = relationship(
        "Connection",
        foreign_keys="Connection.friend_id",
        back_populates="friend",
        cascade="all, delete-orphan",
    )

    password_reset_tokens = relationship(
        "PasswordResetToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )


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
        UUID(as_uuid=True),
        ForeignKey("users.users.id", ondelete="CASCADE"),
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
    __table_args__ = {"schema": "users"}

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
    )
    token = Column(Text, unique=True, nullable=False, index=True)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.users.id", ondelete="CASCADE"),
        nullable=True,
    )
    username = Column(String(255), nullable=True)
    blacklisted_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at = Column(DateTime(timezone=True), nullable=False)


class PasswordResetToken(Base):
    __tablename__ = "password_resets"
    __table_args__ = {"schema": "users"}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token = Column(String(128), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    user = relationship("User", back_populates="password_reset_tokens")
