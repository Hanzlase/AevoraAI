"""Staff triage and management endpoints for handoffs and appointment requests."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.appointment import AppointmentRequest
from app.schemas.chat import (
    AppointmentResponse,
    HandoffResponse,
    HandoffUpdateRequest,
)
from app.services.handoff_service import HandoffService

router = APIRouter(prefix="/staff", tags=["Staff Management"])


@router.get("/handoffs", response_model=list[HandoffResponse])
def list_staff_handoffs(
    status_filter: str | None = Query(None, alias="status", description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
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

    return HandoffResponse(
        id=updated.id,
        conversation_id=updated.conversation_id,
        reason=updated.reason,
        summary=updated.summary,
        status=updated.status,
        created_at=updated.created_at,
    )


@router.get("/appointments", response_model=list[AppointmentResponse])
def list_staff_appointments(
    status_filter: str | None = Query(None, alias="status", description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
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
