# services/db_init/app/models.py
import uuid

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Index
)
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.sql import func, text
from sqlalchemy.orm import relationship, DeclarativeBase



class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "users"}

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    profile_picture_url = Column(String(255), nullable=True)
    last_login = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    password_reset_tokens = relationship(
        "PasswordResetToken", back_populates="user"
    )


class BlacklistedToken(Base):
    __tablename__ = "blacklisted_tokens"
    __table_args__ = {"schema": "users"}

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
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


class UserStatus(Base):
    __tablename__ = "presence"
    __table_args__ = (
        CheckConstraint(
            "status IN ('online', 'away', 'offline')",
            name="valid_status_check",
        ),
        {"schema": "presence"},
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    status = Column(String(10), nullable=False, default="offline")
    last_changed = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

class PasswordResetToken(Base):
    __tablename__ = "password_resets"
    __table_args__ = {"schema": "users"}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.users.id", ondelete="CASCADE"),
        nullable=False,
    token = Column(String(128), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    user = relationship("User", back_populates="password_reset_tokens")


class Connection(Base):
    __tablename__ = "connections"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'accepted', 'rejected', 'blocked')",
            name="ck_connection_status_enum",
        ),
        CheckConstraint(
            "user_id != friend_id",
            name="ck_user_friend_different",
        ),
        UniqueConstraint('user_id', 'friend_id', name='unique_connection'),
        Index('idx_connection_user', 'user_id'),
        Index('idx_connection_friend', 'friend_id'),
        Index('idx_connection_user_friend', 'user_id', 'friend_id', unique=True),
        {
            "comment": (
            "Stores the connection status between two users "
            "and when it was last updated"
        ),
         "schema": "connections"
         },
    )

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.users.id", ondelete="CASCADE"), nullable=False)
    friend_id = Column(UUID(as_uuid=True), ForeignKey("users.users.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(10), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
