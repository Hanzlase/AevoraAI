"""Conversation ORM model."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


def generate_uuid() -> str:
    """Generate string UUID."""
    return str(uuid.uuid4())


class Conversation(Base):
    """Represents a chat conversation thread."""

    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    channel: Mapped[str] = mapped_column(String(32), default="web", nullable=False)
    external_user_id: Mapped[str] = mapped_column(String(128), default="anonymous", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    preferred_language: Mapped[str] = mapped_column(String(16), default="en", nullable=False)
    active_workflow: Mapped[str | None] = mapped_column(String(64), nullable=True)
    workflow_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    last_message_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )
    appointments = relationship(
        "AppointmentRequest",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )
    handoffs = relationship(
        "HandoffRequest",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )
