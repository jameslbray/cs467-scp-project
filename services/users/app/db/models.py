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

from shared.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), nullable=False, unique=True, index=True)
    created_at = Column(
        DateTime, nullable=False, server_default=func.now()
    )
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


class UserStatus(Base):
    __tablename__ = "user_status"
    __table_args__ = (
        CheckConstraint(
            "status IN ('online', 'away', 'offline')",
            name="ck_user_status_enum",
        ),
        {"comment": (
            "Stores the current online status of users "
            "and when it was last updated"
        )},
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
