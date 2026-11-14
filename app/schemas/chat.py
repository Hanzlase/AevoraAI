"""Pydantic schemas for chat, conversations, appointments, and handoffs."""

from datetime import datetime

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Incoming user chat request."""

    message: str = Field(..., min_length=1, max_length=2000, description="User message text")
    conversation_id: str | None = Field(
        default=None,
        description="Optional conversation ID to continue an existing thread",
    )
    channel: str = Field(
        default="web",
        description="Originating channel (web, whatsapp, etc.)",
    )
    external_user_id: str = Field(
        default="anonymous",
        description="External identifier for the user / sender",
    )


class SourceCitation(BaseModel):
    """Source reference supporting the assistant's answer."""

    entity_id: str | None = Field(default=None, description="Entity or chunk identifier")
    category: str = Field(..., description="Document category or type")
    section: str = Field(..., description="Document section or header")
    provenance: str = Field(default="unknown", description="Source origin (pdf or json)")


class ChatResponse(BaseModel):
    """Outgoing assistant response payload."""

    conversation_id: str = Field(..., description="Active conversation UUID")
    response: str = Field(..., description="Generated assistant message text")
    language: str = Field(..., description="Detected and matched language (en, ur, roman_ur)")
    intent: str = Field(..., description="Detected user intent")
    sources: list[SourceCitation] = Field(
        default_factory=list,
        description="Grounding source citations",
    )
    workflow: str | None = Field(default=None, description="Active workflow name if any")
    workflow_status: str | None = Field(
        default=None,
        description="Status of the active workflow",
    )
    appointment_id: str | None = Field(
        default=None,
        description="Associated appointment request ID if created",
    )
    handoff_id: str | None = Field(
        default=None,
        description="Associated human staff handoff request ID if triggered",
    )


class MessageItem(BaseModel):
    """Individual message record inside a conversation history."""

    id: str
    role: str
    content: str
    intent: str | None = None
    language: str | None = None
    sources: list[dict] | None = None
    created_at: datetime


class ConversationHistoryResponse(BaseModel):
    """Full message history of a conversation."""

    conversation_id: str
    channel: str
    external_user_id: str
    status: str
    preferred_language: str
    created_at: datetime
    last_message_at: datetime
    messages: list[MessageItem]


class AppointmentResponse(BaseModel):
    """Representation of an appointment request record."""

    id: str
    conversation_id: str
    patient_name: str
    doctor_id: str | None = None
    doctor_name: str | None = None
    department: str | None = None
    preferred_date: str
    preferred_time: str
    reason: str | None = None
    callback_number: str | None = None
    status: str
    created_at: datetime


class HandoffResponse(BaseModel):
    """Representation of a human staff handoff record."""

    id: str
    conversation_id: str
    reason: str
    summary: str
    status: str
    created_at: datetime


class HandoffUpdateRequest(BaseModel):
    """Payload to update handoff status."""

    status: str = Field(..., description="New status (in_progress, resolved, closed)")
