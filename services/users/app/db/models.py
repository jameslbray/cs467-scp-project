# services/users/app/db/models.py
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import relationship

from services.connections.app.db.models import (
    Connection,  # noqa: F401, SQL alchemy just needs to know about the model
)
from services.shared.base import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("idx_username", "username"),
        {"schema": "users"},
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
    )
    username = Column(String(50), nullable=False, unique=True, index=True)
    display_name = Column(String(100), nullable=True)
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

    connections = relationship(
        "Connection",
        foreign_keys="Connection.user_id",
        primaryjoin="User.id == Connection.user_id",
        viewonly=True,  # This makes it read-only and avoids the back_populates requirement
    )

    friends = relationship(
        "Connection",
        foreign_keys="Connection.friend_id",
        primaryjoin="User.id == Connection.friend_id",
        viewonly=True,  # This makes it read-only and avoids the back_populates requirement
    )

    password_reset_tokens = relationship(
        "PasswordResetToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )


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
