# services/db_init/app/models.py
import uuid

from sqlalchemy import CheckConstraint, Column, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "users"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    profile_picture_url = Column(String(255), nullable=True)
    last_login = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True),
                        server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(
    ), onupdate=func.now(), nullable=False)


class BlacklistedToken(Base):
    __tablename__ = "blacklisted_tokens"
    __table_args__ = {"schema": "users"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token = Column(Text, unique=True, nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey(
        "users.users.id", ondelete="CASCADE"), nullable=True)
    username = Column(String(255), nullable=True)
    blacklisted_at = Column(TIMESTAMP(timezone=True),
                            server_default=func.now(), nullable=False)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)


class UserStatus(Base):
    __tablename__ = "presence"
    __table_args__ = (
        CheckConstraint("status IN ('online', 'away', 'offline')",
                        name="valid_status_check"),
        {"schema": "presence"}
    )

    user_id = Column(UUID(as_uuid=True),
                     ForeignKey(
            "users.users.id", ondelete="CASCADE"), primary_key=True)
    status = Column(
        String(10), nullable=False, default="offline")
    last_changed = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False, index=True)


class Connection(Base):
    __tablename__ = "connections"
    __table_args__ = {"schema": "presence"}

    user_id = Column(
        UUID(as_uuid=True), ForeignKey(
            "users.users.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False)
    connected_user_id = Column(
        UUID(as_uuid=True), ForeignKey(
            "users.users.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False)
    connection_status = Column(
        Text, nullable=False, index=True)
    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(), nullable=False)
