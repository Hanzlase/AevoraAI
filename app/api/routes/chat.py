"""Chat API endpoints for Aevora AI virtual receptionist."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ConversationHistoryResponse,
)
from app.services.conversation_service import ConversationService

router = APIRouter(prefix="/chat", tags=["Chat & Conversations"])


@router.post("", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def send_chat_message(
    request: ChatRequest,
    db: Session = Depends(get_db),
) -> ChatResponse:
    """Send a message to Aevora AI receptionist and receive a context-grounded response."""
    try:
        return await ConversationService.process_chat(db=db, request=request)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while processing your message: {exc}",
        ) from exc


@router.get(
    "/{conversation_id}/history",
    response_model=ConversationHistoryResponse,
    status_code=status.HTTP_200_OK,
)
def get_chat_history(
    conversation_id: str,
    db: Session = Depends(get_db),
) -> ConversationHistoryResponse:
    """Retrieve full conversation history for a given conversation ID."""
    history = ConversationService.get_conversation_history(db=db, conversation_id=conversation_id)
    if not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conversation_id}' not found.",
        )
    return history


@router.delete("/{conversation_id}", status_code=status.HTTP_200_OK)
def delete_chat_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
) -> dict:
    """Delete a conversation session and all its associated messages."""
    deleted = ConversationService.delete_conversation(db=db, conversation_id=conversation_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conversation_id}' not found.",
        )
    return {"status": "deleted", "conversation_id": conversation_id}
