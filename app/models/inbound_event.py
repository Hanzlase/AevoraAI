"""InboundEvent ORM model for durable webhook event queuing and idempotency."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


def generate_uuid() -> str:
    """Generate string UUID."""
    return str(uuid.uuid4())


class InboundEvent(Base):
    """Represents an incoming webhook event from messaging providers (e.g. Meta WhatsApp).

    Provides durable persistence, deduplication via unique provider message IDs,
    and asynchronous bounded worker consumption.
    """

    __tablename__ = "inbound_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    provider_message_id: Mapped[str | None] = mapped_column(
        String(128),
        unique=True,
        index=True,
        nullable=True,
    )
    channel: Mapped[str] = mapped_column(String(32), default="whatsapp", nullable=False)
    sender_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )  # text, audio, status, unsupported
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        default="pending",
        nullable=False,
        index=True,
    )  # pending, processing, processed, failed
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

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
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (Index("ix_inbound_events_status_created", "status", "created_at"),)
