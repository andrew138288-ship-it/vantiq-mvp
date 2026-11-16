import re
import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class RegisterRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=12, max_length=128)
    display_name: str = Field(min_length=1, max_length=160)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("A valid email address is required")
        return value

    @field_validator("display_name")
    @classmethod
    def normalize_display_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("A name is required")
        return value


class RegistrationAccepted(BaseModel):
    message: str


class EmailVerificationConfirm(BaseModel):
    token: str = Field(min_length=32, max_length=256)


class LoginRequest(BaseModel):
    email: str
    password: str
    tenant_id: uuid.UUID | None = None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("A valid email address is required")
        return value


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

    @model_validator(mode="after")
    def reject_null_display_name(self):
        if "display_name" in self.model_fields_set and self.display_name is None:
            raise ValueError("display_name cannot be null")
        return self


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


class SalesAssistRequest(BaseModel):
    response_locale: str = Field(default="en-US", min_length=2, max_length=16)
    sales_goal: str | None = Field(default=None, max_length=500)


class SalesStrategy(BaseModel):
    name: str
    objective: str
    rationale: str
    next_move: str
    risk: str


class SalesDecision(BaseModel):
    customer_situation: str
    buying_stage: str
    buying_signals: list[str]
    objections: list[str]
    strategy_1: SalesStrategy
    strategy_2: SalesStrategy
    comparison: str
    selected_strategy: str = Field(pattern="^(strategy_1|strategy_2)$")
    selection_reason: str
    suggested_reply: str
    before_sending: list[str]


class SalesAssistResponse(BaseModel):
    conversation_id: uuid.UUID
    suggestion: str
    decision: SalesDecision
    model: str
    generated_at: datetime
    requires_human_review: bool = True


class PasswordResetRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("A valid email address is required")
        return value


class PasswordResetConfirm(BaseModel):
    token: str = Field(min_length=32, max_length=256)
    new_password: str = Field(min_length=12, max_length=128)
