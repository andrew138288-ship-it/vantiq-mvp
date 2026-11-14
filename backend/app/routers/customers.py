import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..dependencies import get_db, get_current_principal
from ..models import Customer
from ..schemas import CustomerCreate, CustomerUpdate, CustomerPublic

router = APIRouter(prefix="/customers", tags=["customers"])


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
