import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from medical_api.core.config import get_settings
from medical_api.core.security import create_access_token, hash_password, verify_password
from medical_api.modules.identity.models import (
    PasswordResetToken,
    RefreshToken,
    RoleName,
    User,
    UserInvite,
)
from medical_api.modules.identity.repository import (
    InviteRepository,
    PasswordResetRepository,
    RefreshTokenRepository,
    UserRepository,
)
from medical_api.modules.identity.schemas import RegisterOrganizationRequest, TokenResponse
from medical_api.modules.organizations.models import Organization
from medical_api.shared.utilities.tokens import generate_opaque_token, hash_token

settings = get_settings()


class AuthService:
    def __init__(
        self,
        session: AsyncSession,
        users: UserRepository,
        refresh_tokens: RefreshTokenRepository,
        invites: InviteRepository,
        password_resets: PasswordResetRepository,
    ):
        self.session = session
        self.users = users
        self.refresh_tokens = refresh_tokens
        self.invites = invites
        self.password_resets = password_resets

    async def _issue_tokens(self, user: User) -> TokenResponse:
        roles = await self.users.get_roles(user.id)
        access_token = create_access_token(
            subject=str(user.id),
            extra_claims={"organization_id": str(user.organization_id), "roles": roles},
        )
        raw_refresh, refresh_hash = generate_opaque_token()
        now = datetime.now(UTC)
        await self.refresh_tokens.create(
            RefreshToken(
                user_id=user.id,
                token_hash=refresh_hash,
                expires_at=now + timedelta(days=settings.refresh_token_expire_days),
                created_at=now,
            )
        )
        return TokenResponse(access_token=access_token, refresh_token=raw_refresh)

    async def register_organization(
        self, data: RegisterOrganizationRequest
    ) -> tuple[Organization, TokenResponse]:
        """One-time bootstrap for this product's single clinic.

        This product is single-tenant: there is exactly one organization,
        ever. In production this endpoint must never be reachable at all
        (see the router's environment gate) — a production deployment is
        bootstrapped once via an operator-run seed command, not this public
        HTTP call. It stays open in non-production environments purely so
        local dev and the test suite can create disposable clinics.
        """
        organization = Organization(name=data.organization_name)
        self.session.add(organization)
        await self.session.flush()

        admin_role = await self.users.get_or_create_role(RoleName.ORGANIZATION_ADMIN)
        user = User(
            organization_id=organization.id,
            email=data.admin_email,
            hashed_password=hash_password(data.admin_password),
            full_name=data.admin_full_name,
        )
        await self.users.create(user)
        await self.users.assign_role(user.id, admin_role.id)

        tokens = await self._issue_tokens(user)
        return organization, tokens

    async def login(self, email: str, password: str) -> TokenResponse:
        user = await self.users.get_by_email_any_org(email)
        if (
            user is None
            or not user.is_active
            or not verify_password(password, user.hashed_password)
        ):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
        return await self._issue_tokens(user)

    async def refresh(self, raw_refresh_token: str) -> TokenResponse:
        token = await self.refresh_tokens.get_by_hash(hash_token(raw_refresh_token))
        now = datetime.now(UTC)
        if token is None or token.revoked_at is not None or token.expires_at < now:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired refresh token")
        # Rotation: the presented token is single-use even if it hasn't expired yet.
        await self.refresh_tokens.revoke(token, now)
        user = await self.users.get_by_id(token.user_id)
        if user is None or not user.is_active:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired refresh token")
        return await self._issue_tokens(user)

    async def logout(self, raw_refresh_token: str) -> None:
        token = await self.refresh_tokens.get_by_hash(hash_token(raw_refresh_token))
        if token is not None and token.revoked_at is None:
            await self.refresh_tokens.revoke(token, datetime.now(UTC))

    async def create_invite(
        self, organization_id: uuid.UUID, invited_by_user_id: uuid.UUID, email: str, role: RoleName
    ) -> tuple[UserInvite, str]:
        raw_token, token_hash = generate_opaque_token()
        invite = UserInvite(
            organization_id=organization_id,
            email=email,
            role=role,
            invited_by_user_id=invited_by_user_id,
            token_hash=token_hash,
            expires_at=datetime.now(UTC) + timedelta(days=settings.invite_expire_days),
        )
        await self.invites.create(invite)
        return invite, raw_token

    async def accept_invite(self, raw_token: str, full_name: str, password: str) -> TokenResponse:
        invite = await self.invites.get_by_token_hash(hash_token(raw_token))
        now = datetime.now(UTC)
        if invite is None or invite.accepted_at is not None or invite.expires_at < now:
            raise HTTPException(status.HTTP_410_GONE, "Invite not found, already used, or expired")

        existing = await self.users.get_by_email(invite.organization_id, invite.email)
        if existing is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT, "An account with this email already exists"
            )

        user = User(
            organization_id=invite.organization_id,
            email=invite.email,
            hashed_password=hash_password(password),
            full_name=full_name,
        )
        await self.users.create(user)
        role = await self.users.get_or_create_role(invite.role)
        await self.users.assign_role(user.id, role.id)
        invite.accepted_at = now

        return await self._issue_tokens(user)

    async def request_password_reset(self, email: str) -> str | None:
        """Returns the raw reset token if an active account exists, else
        None. Callers must respond with the same status/shape either way
        (only whether `token` is populated differs) so the endpoint doesn't
        leak account existence.
        """
        user = await self.users.get_by_email_any_org(email)
        if user is None or not user.is_active:
            return None
        raw_token, token_hash = generate_opaque_token()
        await self.password_resets.create(
            PasswordResetToken(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=datetime.now(UTC)
                + timedelta(hours=settings.password_reset_expire_hours),
            )
        )
        return raw_token

    async def reset_password(self, raw_token: str, new_password: str) -> None:
        reset_token = await self.password_resets.get_by_token_hash(hash_token(raw_token))
        now = datetime.now(UTC)
        if reset_token is None or reset_token.used_at is not None or reset_token.expires_at < now:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired reset token")
        user = await self.users.get_by_id(reset_token.user_id)
        if user is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired reset token")
        user.hashed_password = hash_password(new_password)
        reset_token.used_at = now
