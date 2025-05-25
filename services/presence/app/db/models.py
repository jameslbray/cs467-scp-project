from services.shared.base import Base
from sqlalchemy import (
    CheckConstraint,
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


class UserStatus(Base):
    __tablename__ = "presence"
    __table_args__ = (
        CheckConstraint(
            "status IN ('online', 'away', 'offline')",
            name="ck_user_status_enum",
        ),
        {
            "schema": "presence",
            "extend_existing": True, 
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