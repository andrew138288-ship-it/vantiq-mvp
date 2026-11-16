import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from ..dependencies import get_db, get_current_principal
from ..models import Customer, Conversation, Message
from ..schemas import ConversationCreate, ConversationPublic, MessageCreate, MessagePublic

router = APIRouter(tags=["conversations"])
MAX_AUTHORIZED_MESSAGES = 20


def _get_conversation(db: Session, conversation_id: uuid.UUID, tenant_id: uuid.UUID) -> Conversation:
    conversation = db.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.tenant_id == tenant_id,
        )
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.post("/conversations", response_model=ConversationPublic, status_code=status.HTTP_201_CREATED)
def create_conversation(
    payload: ConversationCreate,
    principal: dict = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    customer = db.scalar(
        select(Customer).where(
            Customer.id == payload.customer_id,
            Customer.tenant_id == principal["tenant_id"],
        )
    )
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    conversation = Conversation(
        tenant_id=principal["tenant_id"],
        customer_id=customer.id,
        channel=payload.channel,
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


@router.post("/conversations/{conversation_id}/authorize-context", response_model=ConversationPublic)
def authorize_context(
    conversation_id: uuid.UUID,
    principal: dict = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    conversation = _get_conversation(db, conversation_id, principal["tenant_id"])
    conversation.context_authorized_at = datetime.now(timezone.utc)
    conversation.context_version += 1
    db.commit()
    db.refresh(conversation)
    return conversation


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessagePublic,
    status_code=status.HTTP_201_CREATED,
)
def add_message(
    conversation_id: uuid.UUID,
    payload: MessageCreate,
    principal: dict = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    conversation = _get_conversation(db, conversation_id, principal["tenant_id"])
    if conversation.context_authorized_at is None:
        raise HTTPException(
            status_code=403,
            detail="Explicitly authorize this conversation context before adding messages",
        )
    message_count = db.scalar(
        select(func.count(Message.id)).where(
            Message.conversation_id == conversation.id,
            Message.tenant_id == principal["tenant_id"],
        )
    ) or 0
    if message_count >= MAX_AUTHORIZED_MESSAGES:
        raise HTTPException(
            status_code=422,
            detail=f"A single analysis context cannot exceed {MAX_AUTHORIZED_MESSAGES} messages",
        )
    message = Message(
        tenant_id=principal["tenant_id"],
        conversation_id=conversation.id,
        direction=payload.direction,
        body=payload.body,
        source="user_authorized_context",
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessagePublic])
def list_messages(
    conversation_id: uuid.UUID,
    limit: int = 100,
    principal: dict = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    conversation = _get_conversation(db, conversation_id, principal["tenant_id"])
    if conversation.context_authorized_at is None:
        raise HTTPException(status_code=403, detail="Conversation context has not been authorized")
    if limit < 1 or limit > 200:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 200")
    statement = (
        select(Message)
        .where(
            Message.conversation_id == conversation.id,
            Message.tenant_id == principal["tenant_id"],
        )
        .order_by(Message.created_at.asc())
        .limit(limit)
    )
    return list(db.scalars(statement))
