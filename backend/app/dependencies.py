import uuid
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session
from .db import SessionLocal
from .models import TenantMembership, User
from .security import decode_access_token

_bearer = HTTPBearer(auto_error=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> dict:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Valid bearer token required",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    try:
        claims = decode_access_token(credentials.credentials)
        user_id = uuid.UUID(claims["sub"])
        tenant_id = uuid.UUID(claims["tenant_id"])
    except (jwt.PyJWTError, KeyError, ValueError, TypeError):
        raise unauthorized
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise unauthorized
    if claims.get("token_version", 0) != user.token_version:
        raise unauthorized
    membership = db.scalar(
        select(TenantMembership).where(
            TenantMembership.user_id == user_id,
            TenantMembership.tenant_id == tenant_id,
        )
    )
    if membership is None:
        raise unauthorized
    return {
        "user_id": user_id,
        "tenant_id": tenant_id,
        "role": membership.role,
        "email": user.email,
        "display_name": user.display_name,
    }
