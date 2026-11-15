import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..dependencies import get_db, get_current_principal
from ..models import Conversation, Customer, Message
from ..schemas import SalesAssistRequest, SalesAssistResponse
from ..services.ai_gateway import (
    AIProviderError,
    AIProviderNotConfigured,
    generate_sales_assist,
)

router = APIRouter(tags=["sales intelligence"])


@router.post(
    "/conversations/{conversation_id}/sales-assist",
    response_model=SalesAssistResponse,
)
async def sales_assist(
    conversation_id: uuid.UUID,
    payload: SalesAssistRequest,
    principal: dict = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    conversation = db.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.tenant_id == principal["tenant_id"],
        )
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conversation.context_authorized_at is None:
        raise HTTPException(
            status_code=403,
            detail="Explicitly authorize this conversation context before AI analysis",
        )
    customer = db.scalar(
        select(Customer).where(
            Customer.id == conversation.customer_id,
            Customer.tenant_id == principal["tenant_id"],
        )
    )
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    messages = list(
        db.scalars(
            select(Message)
            .where(
                Message.conversation_id == conversation.id,
                Message.tenant_id == principal["tenant_id"],
            )
            .order_by(Message.created_at.asc())
            .limit(40)
        )
    )
    if not messages:
        raise HTTPException(status_code=422, detail="At least one authorized message is required")

    transcript = "\n".join(
        f"{'Customer' if message.direction == 'inbound' else 'Salesperson'}: {message.body}"
        for message in messages
    )
    customer_context = (
        f"Customer name: {customer.display_name}\n"
        f"Preferred locale: {customer.preferred_locale or 'not specified'}\n"
        f"Customer notes: {customer.notes or 'none'}\n"
    )
    bounded_context = (customer_context + "\n" + transcript)[-24000:]
    try:
        decision, model = await generate_sales_assist(
            conversation_text=bounded_context,
            response_locale=payload.response_locale,
            sales_goal=payload.sales_goal,
        )
    except AIProviderNotConfigured:
        raise HTTPException(status_code=503, detail="AI provider is not configured")
    except AIProviderError:
        raise HTTPException(status_code=502, detail="AI provider request failed")

    return SalesAssistResponse(
        conversation_id=conversation.id,
        suggestion=decision.suggested_reply,
        decision=decision,
        model=model,
        generated_at=datetime.now(timezone.utc),
        requires_human_review=True,
    )
