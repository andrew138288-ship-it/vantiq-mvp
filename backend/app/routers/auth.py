import hashlib
import logging
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..dependencies import get_db, get_current_principal
from ..models import Tenant, User, TenantMembership, PasswordResetToken
from ..rate_limit import limiter
from ..schemas import (
    RegisterRequest, LoginRequest, TokenResponse, UserPublic,
    PasswordResetRequest, PasswordResetConfirm,
)
from ..security import hash_password, verify_password, create_access_token
from ..email import send_password_reset_email

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["authentication"])
RESET_TOKEN_MINUTES = 30


def _slugify(value: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:55] or "workspace"
    return f"{base}-{uuid.uuid4().hex[:8]}"


def _token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/hour")
def register(request: Request, payload: RegisterRequest, db: Session = Depends(get_db)):
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
@limiter.limit("5/minute")
def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)):
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


@router.post("/password-reset/request", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("3/hour")
def request_password_reset(
    request: Request,
    payload: PasswordResetRequest,
    db: Session = Depends(get_db),
):
    # Always return the same response to prevent account enumeration.
    generic_response = {"message": "If the account exists, password reset instructions will be sent."}
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not user.is_active:
        return generic_response

    now = datetime.now(timezone.utc)
    db.execute(
        update(PasswordResetToken)
        .where(PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None))
        .values(used_at=now)
    )
    raw_token = secrets.token_urlsafe(32)
    reset = PasswordResetToken(
        user_id=user.id,
        token_hash=_token_digest(raw_token),
        expires_at=now + timedelta(minutes=RESET_TOKEN_MINUTES),
    )
    db.add(reset)
    db.commit()
    try:
        send_password_reset_email(user.email, raw_token)
    except Exception:
        logger.exception("Password reset email could not be sent")
        # Do not expose account existence or SMTP details to the caller.
    return generic_response


@router.post("/password-reset/confirm")
@limiter.limit("5/hour")
def confirm_password_reset(
    request: Request,
    payload: PasswordResetConfirm,
    db: Session = Depends(get_db),
):
    reset = db.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == _token_digest(payload.token)
        )
    )
    now = datetime.now(timezone.utc)
    if reset is None or reset.used_at is not None:
        raise HTTPException(status_code=400, detail="Reset token is invalid or expired")
    expires_at = reset.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now:
        raise HTTPException(status_code=400, detail="Reset token is invalid or expired")

    user = db.get(User, reset.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=400, detail="Reset token is invalid or expired")

    user.password_hash = hash_password(payload.new_password)
    db.execute(
        update(PasswordResetToken)
        .where(PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None))
        .values(used_at=now)
    )
    db.commit()
    return {"message": "Password has been reset. Please sign in with your new password."}


@router.get("/me", response_model=UserPublic)
def me(principal: dict = Depends(get_current_principal)):
    return UserPublic(
        id=principal["user_id"], email=principal["email"],
        display_name=principal["display_name"], tenant_id=principal["tenant_id"],
        role=principal["role"]
    )
