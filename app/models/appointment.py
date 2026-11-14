"""AppointmentRequest ORM model."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


def generate_uuid() -> str:
    """Generate string UUID."""
    return str(uuid.uuid4())


class AppointmentRequest(Base):
    """Represents an appointment intake request collected by the assistant.

    Note: Aevora is an AI receptionist assistant and does not directly book into
    live clinical EMR calendars without human/staff review. The primary valid status
    is 'pending_staff_confirmation'.
    """

    __tablename__ = "appointment_requests"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    conversation_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    patient_name: Mapped[str] = mapped_column(String(128), nullable=False)
    doctor_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    doctor_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    department: Mapped[str | None] = mapped_column(String(128), nullable=True)
    preferred_date: Mapped[str] = mapped_column(String(64), nullable=False)
    preferred_time: Mapped[str] = mapped_column(String(64), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    callback_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        default="pending_staff_confirmation",
        nullable=False,
        index=True,
    )  # draft, pending_staff_confirmation, reviewed, cancelled

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

    conversation = relationship("Conversation", back_populates="appointments")
