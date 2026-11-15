"""Staff triage, administration, authentication, and monitoring endpoints."""

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import (
    create_access_token,
    get_current_staff,
    verify_password,
)
from app.core.config import Settings, get_settings
from app.database.session import get_db
from app.models.appointment import AppointmentRequest
from app.models.conversation import Conversation
from app.models.handoff import HandoffRequest
from app.models.inbound_event import InboundEvent
from app.models.message import Message
from app.models.user import StaffUser
from app.schemas.chat import (
    AppointmentResponse,
    HandoffResponse,
    HandoffUpdateRequest,
    MessageItem,
    SourceCitation,
)
from app.schemas.staff import (
    AppointmentStatusUpdateRequest,
    StaffConversationDetailResponse,
    StaffConversationListItem,
    StaffKBStatusResponse,
    StaffLoginRequest,
    StaffOverviewResponse,
    StaffSystemStatusResponse,
    StaffTokenResponse,
    StaffUserResponse,
)
from app.services.event_worker import get_event_worker
from app.services.handoff_service import HandoffService

logger = logging.getLogger("aevora.api.staff")

router = APIRouter(prefix="/staff", tags=["Staff Management"])


# ==============================================================================
# Authentication Endpoints
# ==============================================================================


@router.post("/auth/login", response_model=StaffTokenResponse)
def staff_login(
    payload: StaffLoginRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> StaffTokenResponse:
    """Authenticate clinic staff member and return signed JWT bearer token."""
    user = db.scalar(select(StaffUser).where(StaffUser.username == payload.username.strip()))
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(payload.password, user.hashed_password, user.salt):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user.last_login_at = datetime.now(UTC)
    db.commit()

    token = create_access_token(user=user, settings=settings)
    return StaffTokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
    )


@router.get("/auth/me", response_model=StaffUserResponse)
def get_current_staff_profile(
    current_staff: StaffUser = Depends(get_current_staff),
) -> StaffUserResponse:
    """Retrieve authenticated staff user profile."""
    return StaffUserResponse(
        id=current_staff.id,
        username=current_staff.username,
        full_name=current_staff.full_name,
        role=current_staff.role,
        is_active=current_staff.is_active,
        created_at=current_staff.created_at,
        last_login_at=current_staff.last_login_at,
    )


@router.post("/auth/logout")
def staff_logout(
    current_staff: StaffUser = Depends(get_current_staff),
) -> dict[str, str]:
    """Client-side token invalidation confirmation."""
    return {"status": "logged_out", "message": f"Goodbye, {current_staff.full_name}."}


# ==============================================================================
# Clinic Operational Overview Metrics
# ==============================================================================


@router.get("/overview", response_model=StaffOverviewResponse)
def get_clinic_overview_metrics(
    db: Session = Depends(get_db),
    current_staff: StaffUser = Depends(get_current_staff),
) -> StaffOverviewResponse:
    """Aggregate real-time counts across conversations, appointments, and handoffs."""
    total_convs = db.scalar(select(func.count(Conversation.id))) or 0
    active_convs = (
        db.scalar(select(func.count(Conversation.id)).where(Conversation.status == "active")) or 0
    )

    pending_appts = (
        db.scalar(
            select(func.count(AppointmentRequest.id)).where(
                AppointmentRequest.status == "pending_staff_confirmation"
            )
        )
        or 0
    )
    confirmed_appts = (
        db.scalar(
            select(func.count(AppointmentRequest.id)).where(
                AppointmentRequest.status == "confirmed_by_staff"
            )
        )
        or 0
    )

    pending_handoffs = (
        db.scalar(select(func.count(HandoffRequest.id)).where(HandoffRequest.status == "pending"))
        or 0
    )
    resolved_handoffs = (
        db.scalar(select(func.count(HandoffRequest.id)).where(HandoffRequest.status == "resolved"))
        or 0
    )

    total_msgs = db.scalar(select(func.count(Message.id))) or 0
    whatsapp_events = db.scalar(select(func.count(InboundEvent.id))) or 0

    return StaffOverviewResponse(
        total_conversations=total_convs,
        active_conversations=active_convs,
        pending_appointments=pending_appts,
        confirmed_appointments=confirmed_appts,
        pending_handoffs=pending_handoffs,
        resolved_handoffs=resolved_handoffs,
        total_messages=total_msgs,
        whatsapp_events_count=whatsapp_events,
    )


# ==============================================================================
# Conversations Management
# ==============================================================================


@router.get("/conversations", response_model=list[StaffConversationListItem])
def list_conversations(
    search: str | None = Query(None, description="Search phone number or conversation ID"),
    channel: str | None = Query(None, description="Filter by channel: whatsapp, web"),
    status_filter: str | None = Query(None, alias="status", description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_staff: StaffUser = Depends(get_current_staff),
) -> list[StaffConversationListItem]:
    """List conversations with search, filtering, and summary indicators."""
    stmt = select(Conversation).order_by(Conversation.last_message_at.desc())

    if channel:
        stmt = stmt.where(Conversation.channel == channel)
    if status_filter:
        stmt = stmt.where(Conversation.status == status_filter)
    if search:
        search_pattern = f"%{search.strip()}%"
        stmt = stmt.where(
            Conversation.external_user_id.ilike(search_pattern)
            | Conversation.id.ilike(search_pattern)
        )

    stmt = stmt.offset(offset).limit(limit)
    convs = list(db.scalars(stmt).all())

    items = []
    for c in convs:
        # Message count and last message
        msg_count = (
            db.scalar(select(func.count(Message.id)).where(Message.conversation_id == c.id)) or 0
        )
        last_msg = db.scalar(
            select(Message)
            .where(Message.conversation_id == c.id)
            .order_by(Message.created_at.desc())
            .limit(1)
        )

        has_pending_appt = bool(
            db.scalar(
                select(AppointmentRequest.id)
                .where(
                    AppointmentRequest.conversation_id == c.id,
                    AppointmentRequest.status == "pending_staff_confirmation",
                )
                .limit(1)
            )
        )

        has_pending_hnd = bool(
            db.scalar(
                select(HandoffRequest.id)
                .where(
                    HandoffRequest.conversation_id == c.id,
                    HandoffRequest.status == "pending",
                )
                .limit(1)
            )
        )

        items.append(
            StaffConversationListItem(
                id=c.id,
                channel=c.channel,
                external_user_id=c.external_user_id,
                status=c.status,
                preferred_language=c.preferred_language,
                active_workflow=c.active_workflow,
                message_count=msg_count,
                last_message_text=last_msg.content[:80] if last_msg else None,
                last_message_at=c.last_message_at,
                has_pending_appointment=has_pending_appt,
                has_pending_handoff=has_pending_hnd,
            )
        )
    return items


@router.get("/conversations/{conversation_id}", response_model=StaffConversationDetailResponse)
def get_conversation_detail(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_staff: StaffUser = Depends(get_current_staff),
) -> StaffConversationDetailResponse:
    """Retrieve full chronological conversation message thread with clinical details."""
    conv = db.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conversation_id}' not found.",
        )

    raw_messages = list(
        db.scalars(
            select(Message)
            .where(Message.conversation_id == conv.id)
            .order_by(Message.created_at.asc())
        ).all()
    )

    msg_items = []
    for m in raw_messages:
        citations = []
        if m.sources and isinstance(m.sources, list):
            for c in m.sources:
                if isinstance(c, dict):
                    citations.append(
                        SourceCitation(
                            entity_id=c.get("entity_id"),
                            category=c.get("category", "clinic_info"),
                            section=c.get("section", "General"),
                            provenance=c.get("provenance", "json"),
                        )
                    )

        msg_items.append(
            MessageItem(
                id=m.id,
                role=m.role,
                content=m.content,
                intent=m.intent,
                language=m.language,
                sources=[c.model_dump() for c in citations],
                created_at=m.created_at,
            )
        )

    raw_appts = list(
        db.scalars(
            select(AppointmentRequest)
            .where(AppointmentRequest.conversation_id == conv.id)
            .order_by(AppointmentRequest.created_at.desc())
        ).all()
    )
    appts = [
        AppointmentResponse(
            id=a.id,
            conversation_id=a.conversation_id,
            patient_name=a.patient_name,
            doctor_id=a.doctor_id,
            doctor_name=a.doctor_name,
            department=a.department,
            preferred_date=a.preferred_date,
            preferred_time=a.preferred_time,
            reason=a.reason,
            callback_number=a.callback_number,
            status=a.status,
            created_at=a.created_at,
        )
        for a in raw_appts
    ]

    raw_handoffs = list(
        db.scalars(
            select(HandoffRequest)
            .where(HandoffRequest.conversation_id == conv.id)
            .order_by(HandoffRequest.created_at.desc())
        ).all()
    )
    handoffs = [
        HandoffResponse(
            id=h.id,
            conversation_id=h.conversation_id,
            reason=h.reason,
            summary=h.summary,
            status=h.status,
            created_at=h.created_at,
        )
        for h in raw_handoffs
    ]

    return StaffConversationDetailResponse(
        id=conv.id,
        channel=conv.channel,
        external_user_id=conv.external_user_id,
        status=conv.status,
        preferred_language=conv.preferred_language,
        active_workflow=conv.active_workflow,
        created_at=conv.created_at,
        last_message_at=conv.last_message_at,
        messages=msg_items,
        appointments=appts,
        handoffs=handoffs,
    )


# ==============================================================================
# Appointments Management
# ==============================================================================


@router.get("/appointments", response_model=list[AppointmentResponse])
def list_staff_appointments(
    status_filter: str | None = Query(None, alias="status", description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_staff: StaffUser = Depends(get_current_staff),
) -> list[AppointmentResponse]:
    """List appointment requests submitted by patients."""
    stmt = select(AppointmentRequest).order_by(AppointmentRequest.created_at.desc()).limit(limit)
    if status_filter:
        stmt = stmt.where(AppointmentRequest.status == status_filter)

    records = list(db.scalars(stmt).all())
    return [
        AppointmentResponse(
            id=a.id,
            conversation_id=a.conversation_id,
            patient_name=a.patient_name,
            doctor_id=a.doctor_id,
            doctor_name=a.doctor_name,
            department=a.department,
            preferred_date=a.preferred_date,
            preferred_time=a.preferred_time,
            reason=a.reason,
            callback_number=a.callback_number,
            status=a.status,
            created_at=a.created_at,
        )
        for a in records
    ]


@router.patch("/appointments/{appointment_id}", response_model=AppointmentResponse)
def update_appointment_status(
    appointment_id: str,
    payload: AppointmentStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_staff: StaffUser = Depends(get_current_staff),
) -> AppointmentResponse:
    """Update appointment request status (e.g. confirm by staff or cancel)."""
    valid_statuses = {
        "pending_staff_confirmation",
        "reviewed",
        "confirmed_by_staff",
        "cancelled",
    }
    if payload.status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status '{payload.status}'. Allowed: {sorted(valid_statuses)}",
        )

    appt = db.get(AppointmentRequest, appointment_id)
    if not appt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment request '{appointment_id}' not found.",
        )

    appt.status = payload.status
    db.commit()
    db.refresh(appt)
    logger.info(
        f"Staff '{current_staff.username}' updated appointment {appt.id} status to '{appt.status}'"
    )

    return AppointmentResponse(
        id=appt.id,
        conversation_id=appt.conversation_id,
        patient_name=appt.patient_name,
        doctor_id=appt.doctor_id,
        doctor_name=appt.doctor_name,
        department=appt.department,
        preferred_date=appt.preferred_date,
        preferred_time=appt.preferred_time,
        reason=appt.reason,
        callback_number=appt.callback_number,
        status=appt.status,
        created_at=appt.created_at,
    )


# ==============================================================================
# Human Staff Handoffs Management
# ==============================================================================


@router.get("/handoffs", response_model=list[HandoffResponse])
def list_staff_handoffs(
    status_filter: str | None = Query(None, alias="status", description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_staff: StaffUser = Depends(get_current_staff),
) -> list[HandoffResponse]:
    """List staff escalation and handoff requests."""
    records = HandoffService.list_handoffs(db=db, status=status_filter, limit=limit)
    return [
        HandoffResponse(
            id=r.id,
            conversation_id=r.conversation_id,
            reason=r.reason,
            summary=r.summary,
            status=r.status,
            created_at=r.created_at,
        )
        for r in records
    ]


@router.patch("/handoffs/{handoff_id}", response_model=HandoffResponse)
def update_staff_handoff(
    handoff_id: str,
    payload: HandoffUpdateRequest,
    db: Session = Depends(get_db),
    current_staff: StaffUser = Depends(get_current_staff),
) -> HandoffResponse:
    """Update status of a handoff request."""
    try:
        updated = HandoffService.update_status(
            db=db, handoff_id=handoff_id, new_status=payload.status
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        ) from val_err

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Handoff '{handoff_id}' not found.",
        )

    logger.info(
        f"Staff '{current_staff.username}' updated handoff {updated.id} to '{updated.status}'"
    )
    return HandoffResponse(
        id=updated.id,
        conversation_id=updated.conversation_id,
        reason=updated.reason,
        summary=updated.summary,
        status=updated.status,
        created_at=updated.created_at,
    )


# ==============================================================================
# Knowledge Base & System Operational Status
# ==============================================================================


@router.get("/knowledge-base/status", response_model=StaffKBStatusResponse)
def get_knowledge_base_status(
    current_staff: StaffUser = Depends(get_current_staff),
) -> StaffKBStatusResponse:
    """Retrieve indexing metadata and integrity of the clinic RAG knowledge base."""
    manifest_path = Path("data/vector_store/manifest.json")
    if not manifest_path.exists():
        return StaffKBStatusResponse(
            indexed_chunks=0,
            faiss_vectors=0,
            bm25_documents=0,
            last_indexed_at=None,
            source_files=[],
            consistency_notes_count=0,
            index_ready=False,
        )

    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        source_hashes = data.get("source_file_hashes", {})
        source_files = list(source_hashes.keys())
        chunk_count = data.get("chunk_count", 0)
        built_at = data.get("built_at")
        notes = data.get("consistency_issues", [])

        return StaffKBStatusResponse(
            indexed_chunks=chunk_count,
            faiss_vectors=chunk_count,
            bm25_documents=chunk_count,
            last_indexed_at=built_at,
            source_files=source_files,
            consistency_notes_count=len(notes),
            index_ready=True,
        )
    except Exception as exc:
        logger.warning(f"Error reading knowledge base manifest: {exc}")
        return StaffKBStatusResponse(
            indexed_chunks=0,
            faiss_vectors=0,
            bm25_documents=0,
            last_indexed_at=None,
            source_files=[],
            consistency_notes_count=0,
            index_ready=False,
        )


@router.get("/system/status", response_model=StaffSystemStatusResponse)
def get_system_status(
    settings: Settings = Depends(get_settings),
    current_staff: StaffUser = Depends(get_current_staff),
) -> StaffSystemStatusResponse:
    """Live operational diagnostics across all platform integrations."""
    # Worker status
    worker_status = "Disabled"
    if settings.whatsapp_event_worker_enabled:
        worker = get_event_worker()
        worker_status = "Running" if worker.is_running else "Stopped"

    # Gemini status
    gemini_status = "Connected" if settings.gemini_api_key else "Not Configured (Mock Fallback)"

    # WhatsApp status
    whatsapp_status = (
        "Connected"
        if (settings.whatsapp_enabled and settings.whatsapp_access_token)
        else "Offline (Mock Mode)"
    )

    # RAG status
    rag_ready = Path("data/vector_store/faiss_index.bin").exists()
    rag_status = "Ready (Indexed)" if rag_ready else "Index Missing"

    # Whisper status
    whisper_status = f"Ready ({settings.whisper_model_size})"

    return StaffSystemStatusResponse(
        app_name=settings.app_name,
        version=settings.version,
        environment=settings.environment,
        fastapi_status="Operational",
        gemini_status=gemini_status,
        gemini_model=settings.gemini_model,
        whatsapp_status=whatsapp_status,
        whatsapp_phone_number_id=settings.whatsapp_phone_number_id,
        worker_status=worker_status,
        rag_status=rag_status,
        whisper_status=whisper_status,
        whisper_device=settings.whisper_device,
        voice_processing_status="Enabled" if settings.voice_input_enabled else "Disabled",
    )
