import re
import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


class RegisterRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=12, max_length=128)
    display_name: str = Field(min_length=1, max_length=160)
    tenant_name: str = Field(min_length=1, max_length=160)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("A valid email address is required")
        return value


class LoginRequest(BaseModel):
    email: str
    password: str


class UserPublic(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str | None
    tenant_id: uuid.UUID
    role: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


class CustomerCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=200)
    external_ref: str | None = Field(default=None, max_length=160)
    preferred_locale: str | None = Field(default=None, max_length=16)
    notes: str | None = None


class CustomerUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    external_ref: str | None = Field(default=None, max_length=160)
    preferred_locale: str | None = Field(default=None, max_length=16)
    notes: str | None = None


class CustomerPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    display_name: str
    external_ref: str | None
    preferred_locale: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class ConversationCreate(BaseModel):
    customer_id: uuid.UUID
    channel: str = Field(default="whatsapp", min_length=1, max_length=32)


class ConversationPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    customer_id: uuid.UUID
    channel: str
    context_version: int
    context_authorized_at: datetime | None
    is_active: bool
    created_at: datetime


class MessageCreate(BaseModel):
    direction: str = Field(pattern="^(inbound|outbound)$")
    body: str = Field(min_length=1, max_length=12000)


class MessagePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    direction: str
    body: str
    source: str
    created_at: datetime
