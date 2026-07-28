import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from medical_api.core.database import (
    Base,
    OrganizationScopedMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class RoleName(StrEnum):
    PLATFORM_ADMIN = "platform_admin"
    ORGANIZATION_ADMIN = "organization_admin"
    MEDICAL_DIRECTOR = "medical_director"
    PRACTITIONER = "practitioner"
    ASSISTANT = "assistant"
    RECEPTIONIST = "receptionist"
    AUDITOR = "auditor"


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin, OrganizationScopedMixin):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("organization_id", "email", name="uq_users_org_email"),)

    email: Mapped[str] = mapped_column(String(255), index=True)
    hashed_password: Mapped[str]
    full_name: Mapped[str]
    is_active: Mapped[bool] = mapped_column(default=True)


class Role(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "roles"

    name: Mapped[RoleName] = mapped_column(unique=True)
    description: Mapped[str | None]


class UserRole(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "user_roles"
    __table_args__ = (UniqueConstraint("user_id", "role_id", name="uq_user_roles_user_role"),)

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"))


class RefreshToken(Base, UUIDPrimaryKeyMixin):
    """Opaque, hashed, rotated on every use. A JWT access token can't be
    revoked before it expires; this can — logout and refresh-rotation both
    depend on that.
    """

    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class UserInvite(Base, UUIDPrimaryKeyMixin, TimestampMixin, OrganizationScopedMixin):
    """Single-use, hashed, expiring invite for a staff member who doesn't
    have an account yet. Mirrors the consent-request token pattern.
    """

    __tablename__ = "user_invites"

    email: Mapped[str] = mapped_column(String(255), index=True)
    role: Mapped[RoleName]
    invited_by_user_id: Mapped[uuid.UUID]
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PasswordResetToken(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "password_reset_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
