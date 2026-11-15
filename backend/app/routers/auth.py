import re
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from ..dependencies import get_db, get_current_principal
from ..models import Tenant, User, TenantMembership
from ..schemas import RegisterRequest, LoginRequest, TokenResponse, UserPublic
from ..security import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["authentication"])


def _slugify(value: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:55] or "workspace"
    return f"{base}-{uuid.uuid4().hex[:8]}"


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == payload.email)):
        raise HTTPException(status_code=409, detail="Email is already registered")
    tenant = Tenant(name=payload.tenant_name.strip(), slug=_slugify(payload.tenant_name))
    user = User(
        email=payload.email,
        display_name=payload.display_name.strip(),
        password_hash=hash_password(payload.password),
    )
    try:
        db.add(tenant)
        db.flush()
        db.add(user)
        db.flush()
        db.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Account could not be created with these details")
    token = create_access_token(user_id=str(user.id), tenant_id=str(tenant.id), role="owner")
    return TokenResponse(
        access_token=token,
        user=UserPublic(id=user.id, email=user.email, display_name=user.display_name, tenant_id=tenant.id, role="owner"),
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email or password is incorrect")

    memberships = list(
        db.scalars(
            select(TenantMembership)
            .where(TenantMembership.user_id == user.id)
            .order_by(TenantMembership.created_at)
        ).all()
    )
    if not memberships:
        raise HTTPException(status_code=403, detail="No workspace membership is available")

    if payload.tenant_id is not None:
        membership = next((m for m in memberships if m.tenant_id == payload.tenant_id), None)
        if membership is None:
            raise HTTPException(status_code=403, detail="You are not a member of the selected workspace")
    elif len(memberships) > 1:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "workspace_selection_required",
                "message": "This account belongs to multiple workspaces. Submit tenant_id to select one.",
                "workspaces": [{"tenant_id": str(m.tenant_id), "role": m.role} for m in memberships],
            },
        )
    else:
        membership = memberships[0]

    token = create_access_token(
        user_id=str(user.id),
        tenant_id=str(membership.tenant_id),
        role=membership.role,
    )
    return TokenResponse(
        access_token=token,
        user=UserPublic(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            tenant_id=membership.tenant_id,
            role=membership.role,
        ),
    )


@router.get("/me", response_model=UserPublic)
def me(principal: dict = Depends(get_current_principal)):
    return UserPublic(
        id=principal["user_id"], email=principal["email"],
        display_name=principal["display_name"], tenant_id=principal["tenant_id"],
        role=principal["role"]
    )
