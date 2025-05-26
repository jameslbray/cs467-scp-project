from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from services.shared.base import Base


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
        UniqueConstraint("user_id", "friend_id", name="unique_connection"),
        Index("idx_connection_user", "user_id"),
        Index("idx_connection_friend", "friend_id"),
        Index(
            "idx_connection_user_friend", "user_id", "friend_id", unique=True
        ),
        {
            "comment": (
                "Stores the connection status between two users "
                "and when it was last updated"
            ),
            "schema": "connections",
        },
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
    )
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.users.id", ondelete="CASCADE")
    )
    friend_id = Column(
        UUID(as_uuid=True), ForeignKey("users.users.id", ondelete="CASCADE")
    )
    status = Column(String(10), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # # Relationships
    # user = relationship(
    #     "User", foreign_keys=[user_id], back_populates="connections"
    # )
    # friend = relationship(
    #     "User", foreign_keys=[friend_id], back_populates="friends"
    # )
