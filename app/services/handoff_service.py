"""Handoff service managing escalations to human clinic staff."""

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.handoff import HandoffRequest

logger = logging.getLogger("aevora.services.handoff")


class HandoffService:
    """Service handling human receptionist escalations and staff triage."""

    @staticmethod
    def create_handoff(
        db: Session,
        conversation_id: str,
        reason: str,
        summary: str,
    ) -> HandoffRequest:
        """Create a new pending staff handoff record."""
        handoff = HandoffRequest(
            conversation_id=conversation_id,
            reason=reason,
            summary=summary,
            status="pending",
        )
        db.add(handoff)
        db.flush()
        logger.info(
            f"Created staff handoff {handoff.id} for conversation {conversation_id} (reason: {reason})"
        )
        return handoff

    @staticmethod
    def list_handoffs(
        db: Session,
        status: str | None = None,
        limit: int = 50,
    ) -> list[HandoffRequest]:
        """List handoff records, optionally filtered by status."""
        stmt = select(HandoffRequest).order_by(HandoffRequest.created_at.desc()).limit(limit)
        if status:
            stmt = stmt.where(HandoffRequest.status == status)
        return list(db.scalars(stmt).all())

    @staticmethod
    def update_status(
        db: Session,
        handoff_id: str,
        new_status: str,
    ) -> HandoffRequest | None:
        """Update handoff status (e.g. pending -> in_progress -> resolved -> closed)."""
        valid_statuses = {"pending", "in_progress", "resolved", "closed"}
        if new_status not in valid_statuses:
            raise ValueError(f"Invalid status '{new_status}'. Allowed: {valid_statuses}")

        handoff = db.get(HandoffRequest, handoff_id)
        if not handoff:
            return None

        handoff.status = new_status
        db.flush()
        logger.info(f"Updated handoff {handoff_id} status to '{new_status}'")
        return handoff
