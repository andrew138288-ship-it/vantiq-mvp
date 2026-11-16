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
from ..models import (
    Tenant, User, TenantMembership, PasswordResetToken, EmailVerificationToken, RefreshSession,
)
from ..rate_limit import limiter
from ..schemas import (
    RegisterRequest, RegistrationAccepted, EmailVerificationConfirm,
    LoginRequest, TokenResponse, UserPublic,
    PasswordResetRequest, PasswordResetConfirm, RefreshRequest, RefreshResponse, SessionPublic,
)
from ..security import hash_password, verify_password, create_access_token
from ..email import send_password_reset_email, send_email_verification

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["authentication"])
RESET_TOKEN_MINUTES = 30
VERIFICATION_TOKEN_HOURS = 24
REFRESH_TOKEN_DAYS = 30
REGISTRATION_MESSAGE = "If registration can be completed, a verification email will be sent."
RESEND_MESSAGE = "If the account exists and needs verification, an email will be sent."


def _slugify(value: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:55] or "workspace"
    return f"{base}-{uuid.uuid4().hex[:8]}"


def _token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _create_refresh_session(db: Session, user: User, user_agent: str | None) -> str:
    raw = secrets.token_urlsafe(48)
    now = datetime.now(timezone.utc)
    db.add(RefreshSession(user_id=user.id, session_id=uuid.uuid4(), family_id=uuid.uuid4(), token_hash=_token_digest(raw), user_agent=(user_agent or "")[:300] or None, expires_at=now + timedelta(days=REFRESH_TOKEN_DAYS)))
    return raw


def _new_verification_token(db: Session, user: User) -> str:
    now = datetime.now(timezone.utc)
    db.execute(
        update(EmailVerificationToken)
        .where(
            EmailVerificationToken.user_id == user.id,
            EmailVerificationToken.used_at.is_(None),
        )
        .values(used_at=now)
    )
    raw_token = secrets.token_urlsafe(32)
    db.add(
        EmailVerificationToken(
            user_id=user.id,
            token_hash=_token_digest(raw_token),
            expires_at=now + timedelta(hours=VERIFICATION_TOKEN_HOURS),
        )
    )
    return raw_token


@router.post(
    "/register",
    response_model=RegistrationAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit("3/hour")
def register(request: Request, payload: RegisterRequest, db: Session = Depends(get_db)):
    # Same response for new and existing addresses to avoid account enumeration.
    if db.scalar(select(User).where(User.email == payload.email)):
        return {"message": REGISTRATION_MESSAGE}

    display_name = payload.display_name.strip()
    tenant = Tenant(name=display_name, slug=_slugify(display_name))
    user = User(
        email=payload.email,
        display_name=display_name,
        password_hash=hash_password(payload.password),
        is_active=True,
        is_email_verified=False,
        account_status="pending_verification",
    )
    try:
        db.add(tenant)
        db.flush()
        db.add(user)
        db.flush()
        db.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
        raw_token = _new_verification_token(db, user)
        db.commit()
    except IntegrityError:
        db.rollback()
        return {"message": REGISTRATION_MESSAGE}

    try:
        send_email_verification(user.email, raw_token)
    except Exception:
        logger.exception("Registration verification email could not be sent")
        # User can request another message through /resend-verification.
    return {"message": REGISTRATION_MESSAGE}


@router.post("/verify-email")
@limiter.limit("10/hour")
def verify_email(
    request: Request,
    payload: EmailVerificationConfirm,
    db: Session = Depends(get_db),
):
    token = db.scalar(
        select(EmailVerificationToken).where(
            EmailVerificationToken.token_hash == _token_digest(payload.token)
        )
    )
    now = datetime.now(timezone.utc)
    if token is None or token.used_at is not None:
        raise HTTPException(status_code=400, detail="Verification token is invalid or expired")

    expires_at = token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now:
        raise HTTPException(status_code=400, detail="Verification token is invalid or expired")

    user = db.get(User, token.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=400, detail="Verification token is invalid or expired")

    consumed = db.execute(
        update(EmailVerificationToken)
        .where(
            EmailVerificationToken.id == token.id,
            EmailVerificationToken.used_at.is_(None),
        )
        .values(used_at=now)
    )
    if consumed.rowcount != 1:
        db.rollback()
        raise HTTPException(status_code=400, detail="Verification token is invalid or expired")

    user.is_email_verified = True
    user.account_status = "free_active"
    db.execute(
        update(EmailVerificationToken)
        .where(
            EmailVerificationToken.user_id == user.id,
            EmailVerificationToken.id != token.id,
            EmailVerificationToken.used_at.is_(None),
        )
        .values(used_at=now)
    )
    db.commit()
    return {"message": "Email verified. Your free VANTIQ account is now active. You can sign in."}


@router.post("/resend-verification", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("3/hour")
def resend_verification(
    request: Request,
    payload: PasswordResetRequest,
    db: Session = Depends(get_db),
):
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not user.is_active or user.account_status != "pending_verification":
        return {"message": RESEND_MESSAGE}

    raw_token = _new_verification_token(db, user)
    db.commit()
    try:
        send_email_verification(user.email, raw_token)
    except Exception:
        logger.exception("Verification email resend failed")
    return {"message": RESEND_MESSAGE}


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not user.is_active or user.account_status in {"suspended", "closed"} or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email or password is incorrect")
    if user.account_status == "pending_verification" or not user.is_email_verified:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "email_not_verified",
                "message": "Please verify your email before signing in.",
            },
        )

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
        token_version=user.token_version,
    )
    refresh_token = _create_refresh_session(db, user, request.headers.get("user-agent"))
    db.commit()
    return TokenResponse(
        access_token=token,
        refresh_token=refresh_token,
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
    if user is None or not user.is_active or user.account_status != "free_active" or not user.is_email_verified:
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
    if user is None or not user.is_active or user.account_status != "free_active" or not user.is_email_verified:
        raise HTTPException(status_code=400, detail="Reset token is invalid or expired")

    consumed = db.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.id == reset.id,
            PasswordResetToken.used_at.is_(None),
        )
        .values(used_at=now)
    )
    if consumed.rowcount != 1:
        db.rollback()
        raise HTTPException(status_code=400, detail="Reset token is invalid or expired")

    user.password_hash = hash_password(payload.new_password)
    user.token_version += 1
    db.execute(update(RefreshSession).where(RefreshSession.user_id == user.id, RefreshSession.revoked_at.is_(None)).values(revoked_at=now))
    db.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.id != reset.id,
            PasswordResetToken.used_at.is_(None),
        )
        .values(used_at=now)
    )
    db.commit()
    return {"message": "Password has been reset. Please sign in with your new password."}


@router.post("/refresh", response_model=RefreshResponse)
@limiter.limit("30/hour")
def refresh_access_token(request: Request, payload: RefreshRequest, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    row = db.scalar(select(RefreshSession).where(RefreshSession.token_hash == _token_digest(payload.refresh_token)))
    if row is None:
        raise HTTPException(status_code=401, detail="Refresh token is invalid or expired")
    if row.revoked_at is not None:
        db.execute(update(RefreshSession).where(RefreshSession.family_id == row.family_id, RefreshSession.revoked_at.is_(None)).values(revoked_at=now))
        db.commit()
        raise HTTPException(status_code=401, detail="Refresh token reuse detected; please sign in again")
    expires_at = row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now:
        row.revoked_at = now
        db.commit()
        raise HTTPException(status_code=401, detail="Refresh token is invalid or expired")
    consumed = db.execute(update(RefreshSession).where(RefreshSession.id == row.id, RefreshSession.revoked_at.is_(None), RefreshSession.expires_at > now).values(revoked_at=now, last_used_at=now).execution_options(synchronize_session=False))
    if consumed.rowcount != 1:
        db.rollback()
        raise HTTPException(status_code=401, detail="Refresh token is invalid or expired")
    user = db.get(User, row.user_id)
    if user is None or not user.is_active or user.account_status != "free_active" or not user.is_email_verified:
        db.rollback()
        raise HTTPException(status_code=401, detail="Account is not active")
    membership = db.scalar(select(TenantMembership).where(TenantMembership.user_id == user.id).order_by(TenantMembership.created_at))
    if membership is None:
        db.rollback()
        raise HTTPException(status_code=401, detail="Account membership is unavailable")
    raw = secrets.token_urlsafe(48)
    db.add(RefreshSession(user_id=user.id, session_id=row.session_id, family_id=row.family_id, token_hash=_token_digest(raw), user_agent=(request.headers.get("user-agent") or row.user_agent or "")[:300] or None, expires_at=now + timedelta(days=REFRESH_TOKEN_DAYS)))
    access = create_access_token(user_id=str(user.id), tenant_id=str(membership.tenant_id), role=membership.role, token_version=user.token_version)
    db.commit()
    return RefreshResponse(access_token=access, refresh_token=raw)


@router.post("/logout")
def logout(payload: RefreshRequest, db: Session = Depends(get_db)):
    row = db.scalar(select(RefreshSession).where(RefreshSession.token_hash == _token_digest(payload.refresh_token)))
    if row is not None and row.revoked_at is None:
        now = datetime.now(timezone.utc)
        db.execute(update(RefreshSession).where(RefreshSession.user_id == row.user_id, RefreshSession.session_id == row.session_id, RefreshSession.revoked_at.is_(None)).values(revoked_at=now))
        db.commit()
    return {"message": "Logged out"}


@router.post("/logout-all")
def logout_all(principal: dict = Depends(get_current_principal), db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    user = db.get(User, principal["user_id"])
    db.execute(update(RefreshSession).where(RefreshSession.user_id == principal["user_id"], RefreshSession.revoked_at.is_(None)).values(revoked_at=now))
    if user is not None:
        user.token_version += 1
    db.commit()
    return {"message": "All sessions have been revoked"}


@router.get("/sessions", response_model=list[SessionPublic])
def list_sessions(principal: dict = Depends(get_current_principal), db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    rows = list(db.scalars(select(RefreshSession).where(RefreshSession.user_id == principal["user_id"], RefreshSession.revoked_at.is_(None), RefreshSession.expires_at > now).order_by(RefreshSession.created_at.desc())).all())
    latest = {}
    for row in rows:
        latest.setdefault(row.session_id, row)
    return [SessionPublic(session_id=row.session_id, created_at=row.created_at, last_used_at=row.last_used_at, expires_at=row.expires_at, device=(row.user_agent or "Unknown device")[:120]) for row in latest.values()]


@router.delete("/sessions/{session_id}")
def revoke_session(session_id: uuid.UUID, principal: dict = Depends(get_current_principal), db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    result = db.execute(update(RefreshSession).where(RefreshSession.user_id == principal["user_id"], RefreshSession.session_id == session_id, RefreshSession.revoked_at.is_(None)).values(revoked_at=now))
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session revoked"}


@router.get("/me", response_model=UserPublic)
def me(principal: dict = Depends(get_current_principal)):
    return UserPublic(
        id=principal["user_id"], email=principal["email"],
        display_name=principal["display_name"], tenant_id=principal["tenant_id"],
        role=principal["role"]
    )
