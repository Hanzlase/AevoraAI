"""Pydantic schemas for staff dashboard management, authentication, and diagnostics."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.chat import AppointmentResponse, HandoffResponse, MessageItem


class StaffLoginRequest(BaseModel):
    """Staff credential submission."""

    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1, max_length=128)


class StaffTokenResponse(BaseModel):
    """Staff JWT authentication payload."""

    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    full_name: str
    role: str


class StaffUserResponse(BaseModel):
    """Staff user profile data."""

    id: str
    username: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None = None


class StaffOverviewResponse(BaseModel):
    """Aggregated clinical reception metrics."""

    total_conversations: int
    active_conversations: int
    pending_appointments: int
    confirmed_appointments: int
    pending_handoffs: int
    resolved_handoffs: int
    total_messages: int
    whatsapp_events_count: int


class StaffConversationListItem(BaseModel):
    """Conversation summary item for dashboard listings."""

    id: str
    channel: str
    external_user_id: str
    status: str
    preferred_language: str
    active_workflow: str | None = None
    message_count: int
    last_message_text: str | None = None
    last_message_at: datetime
    has_pending_appointment: bool
    has_pending_handoff: bool


class StaffConversationDetailResponse(BaseModel):
    """Full conversation history with clinical associations."""

    id: str
    channel: str
    external_user_id: str
    status: str
    preferred_language: str
    active_workflow: str | None = None
    created_at: datetime
    last_message_at: datetime
    messages: list[MessageItem]
    appointments: list[AppointmentResponse]
    handoffs: list[HandoffResponse]


class AppointmentStatusUpdateRequest(BaseModel):
    """Staff review action on appointment request."""

    status: str = Field(
        ...,
        description="Allowed statuses: pending_staff_confirmation, reviewed, confirmed_by_staff, cancelled",
    )
    notes: str | None = None


class StaffKBStatusResponse(BaseModel):
    """Status of clinic knowledge base and retrieval indexes."""

    indexed_chunks: int
    faiss_vectors: int
    bm25_documents: int
    last_indexed_at: str | None = None
    source_files: list[str]
    consistency_notes_count: int
    index_ready: bool


class StaffSystemStatusResponse(BaseModel):
    """Operational status of system integrations and runtime components."""

    app_name: str
    version: str
    environment: str
    fastapi_status: str
    gemini_status: str
    gemini_model: str
    whatsapp_status: str
    whatsapp_phone_number_id: str | None = None
    worker_status: str
    rag_status: str
    whisper_status: str
    whisper_device: str
    voice_processing_status: str
