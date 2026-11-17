import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from ..dependencies import get_db, get_current_principal
from ..models import Customer, CustomerIdentity, CustomerMemory, CustomerMemoryRevision, CustomerMemoryUpdateEvent
from ..schemas import (
    CustomerCreate, CustomerUpdate, CustomerPublic, CustomerResolveRequest,
    CustomerResolveResponse, CustomerMemoryUpdateRequest, CustomerMemoryPublic,
    CustomerMemoryRevisionPublic,
)

router = APIRouter(prefix="/customers", tags=["customers"])


@router.post("/resolve", response_model=CustomerResolveResponse)
def resolve_customer(
    payload: CustomerResolveRequest,
    principal: dict = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    """Resolve/create a customer only from a verified channel-scoped identity."""
    tenant_id = principal["tenant_id"]
    identity = db.scalar(select(CustomerIdentity).where(
        CustomerIdentity.tenant_id == tenant_id,
        CustomerIdentity.channel == payload.channel,
        CustomerIdentity.external_ref == payload.external_ref,
    ))
    if identity:
        customer = db.scalar(select(Customer).where(
            Customer.id == identity.customer_id, Customer.tenant_id == tenant_id
        ))
        if customer is None:
            raise HTTPException(status_code=409, detail="Customer identity is inconsistent")
        identity.last_seen_at = datetime.now(timezone.utc)
        if payload.display_name != "WhatsApp customer":
            customer.display_name = payload.display_name
        if payload.preferred_locale:
            customer.preferred_locale = payload.preferred_locale
        db.commit()
        db.refresh(customer)
        return CustomerResolveResponse(customer=customer, created=False)

    customer = Customer(
        tenant_id=tenant_id,
        display_name=payload.display_name,
        external_ref=payload.external_ref,
        preferred_locale=payload.preferred_locale,
    )
    db.add(customer)
    db.flush()
    db.add(CustomerIdentity(
        tenant_id=tenant_id,
        customer_id=customer.id,
        channel=payload.channel,
        external_ref=payload.external_ref,
    ))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        identity = db.scalar(select(CustomerIdentity).where(
            CustomerIdentity.tenant_id == tenant_id,
            CustomerIdentity.channel == payload.channel,
            CustomerIdentity.external_ref == payload.external_ref,
        ))
        if identity is None:
            raise HTTPException(status_code=409, detail="Customer identity could not be resolved safely")
        customer = db.scalar(select(Customer).where(
            Customer.id == identity.customer_id, Customer.tenant_id == tenant_id
        ))
        if customer is None:
            raise HTTPException(status_code=409, detail="Customer identity is inconsistent")
        return CustomerResolveResponse(customer=customer, created=False)
    db.refresh(customer)
    return CustomerResolveResponse(customer=customer, created=True)


@router.post("", response_model=CustomerPublic, status_code=status.HTTP_201_CREATED)
def create_customer(
    payload: CustomerCreate,
    principal: dict = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    customer = Customer(tenant_id=principal["tenant_id"], **payload.model_dump())
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@router.get("", response_model=list[CustomerPublic])
def list_customers(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    principal: dict = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    statement = (
        select(Customer)
        .where(Customer.tenant_id == principal["tenant_id"])
        .order_by(Customer.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(statement))


@router.get("/{customer_id}/memory", response_model=CustomerMemoryPublic)
def get_customer_memory(
    customer_id: uuid.UUID,
    principal: dict = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    customer = db.scalar(select(Customer).where(
        Customer.id == customer_id, Customer.tenant_id == principal["tenant_id"]
    ))
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    memory = db.scalar(select(CustomerMemory).where(
        CustomerMemory.customer_id == customer_id,
        CustomerMemory.tenant_id == principal["tenant_id"],
    ))
    if memory is None:
        raise HTTPException(status_code=404, detail="Customer memory not found")
    return memory


@router.get("/{customer_id}/memory/revisions", response_model=list[CustomerMemoryRevisionPublic])
def list_customer_memory_revisions(
    customer_id: uuid.UUID,
    limit: int = Query(default=20, ge=1, le=100),
    principal: dict = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    customer = db.scalar(select(Customer).where(
        Customer.id == customer_id, Customer.tenant_id == principal["tenant_id"]
    ))
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    statement = (
        select(CustomerMemoryRevision)
        .where(
            CustomerMemoryRevision.customer_id == customer_id,
            CustomerMemoryRevision.tenant_id == principal["tenant_id"],
        )
        .order_by(CustomerMemoryRevision.version.desc())
        .limit(limit)
    )
    return list(db.scalars(statement))


@router.post("/{customer_id}/memory", response_model=CustomerMemoryPublic)
def update_customer_memory(
    customer_id: uuid.UUID,
    payload: CustomerMemoryUpdateRequest,
    principal: dict = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    tenant_id = principal["tenant_id"]
    customer = db.scalar(select(Customer).where(
        Customer.id == customer_id, Customer.tenant_id == tenant_id
    ))
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    if payload.source_conversation_id is not None:
        from ..models import Conversation
        conversation = db.scalar(select(Conversation).where(
            Conversation.id == payload.source_conversation_id,
            Conversation.customer_id == customer_id,
            Conversation.tenant_id == tenant_id,
            Conversation.context_authorized_at.is_not(None),
        ))
        if conversation is None:
            raise HTTPException(status_code=403, detail="Source conversation is not authorized for this customer")
        if payload.context_version is not None and payload.context_version != conversation.context_version:
            raise HTTPException(status_code=409, detail="Conversation context version is stale")

    prior_event = db.scalar(select(CustomerMemoryUpdateEvent).where(
        CustomerMemoryUpdateEvent.tenant_id == tenant_id,
        CustomerMemoryUpdateEvent.customer_id == customer_id,
        CustomerMemoryUpdateEvent.idempotency_key == payload.idempotency_key,
    ))
    memory = db.scalar(select(CustomerMemory).where(
        CustomerMemory.tenant_id == tenant_id,
        CustomerMemory.customer_id == customer_id,
    ))
    if prior_event:
        if memory is None:
            raise HTTPException(status_code=409, detail="Memory event exists without current memory")
        return memory

    current_version = memory.version if memory else 0
    if current_version != payload.expected_version:
        raise HTTPException(status_code=409, detail={
            "code": "memory_version_conflict",
            "current_version": current_version,
        })

    next_version = current_version + 1
    if memory is None:
        memory = CustomerMemory(
            tenant_id=tenant_id, customer_id=customer_id,
            summary=payload.summary, structured_data=payload.structured_data,
            version=next_version,
        )
        db.add(memory)
        db.flush()
    else:
        memory.summary = payload.summary
        memory.structured_data = payload.structured_data
        memory.version = next_version

    revision = CustomerMemoryRevision(
        tenant_id=tenant_id,
        customer_id=customer_id,
        version=next_version,
        summary=payload.summary,
        structured_data=payload.structured_data,
        provenance=payload.provenance,
        source_conversation_id=payload.source_conversation_id,
        context_version=payload.context_version,
    )
    db.add(revision)
    db.flush()
    db.add(CustomerMemoryUpdateEvent(
        tenant_id=tenant_id,
        customer_id=customer_id,
        idempotency_key=payload.idempotency_key,
        revision_id=revision.id,
    ))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Concurrent memory update detected; reload before retrying")
    db.refresh(memory)
    return memory


@router.get("/{customer_id}", response_model=CustomerPublic)
def get_customer(
    customer_id: uuid.UUID,
    principal: dict = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    customer = db.scalar(
        select(Customer).where(
            Customer.id == customer_id,
            Customer.tenant_id == principal["tenant_id"],
        )
    )
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.patch("/{customer_id}", response_model=CustomerPublic)
def update_customer(
    customer_id: uuid.UUID,
    payload: CustomerUpdate,
    principal: dict = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    customer = db.scalar(
        select(Customer).where(
            Customer.id == customer_id,
            Customer.tenant_id == principal["tenant_id"],
        )
    )
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(customer, key, value)
    db.commit()
    db.refresh(customer)
    return customer
