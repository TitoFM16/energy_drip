import uuid

from pydantic import BaseModel, EmailStr, Field

from medical_api.modules.identity.models import RoleName


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class UserRead(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    email: EmailStr
    full_name: str
    roles: list[str]

    model_config = {"from_attributes": True}


class RegisterOrganizationRequest(BaseModel):
    organization_name: str = Field(min_length=1)
    admin_email: EmailStr
    admin_password: str = Field(min_length=8, max_length=72)
    admin_full_name: str = Field(min_length=1)


class RegisterOrganizationResponse(TokenResponse):
    organization_id: uuid.UUID


class InviteCreate(BaseModel):
    email: EmailStr
    role: RoleName


class InviteCreateResponse(BaseModel):
    invite_id: uuid.UUID
    # Dev-mode convenience: the raw token is returned directly so the flow is
    # testable without an email/WhatsApp integration wired up. In production
    # this must be delivered out-of-band (email) and never returned here.
    token: str


class InviteAcceptRequest(BaseModel):
    full_name: str = Field(min_length=1)
    password: str = Field(min_length=8, max_length=72)


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetRequestResponse(BaseModel):
    detail: str
    # Dev-mode convenience only — see InviteCreateResponse.token note above.
    token: str | None = None


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=72)
