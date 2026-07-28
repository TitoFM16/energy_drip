import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from medical_api.api.dependencies import AuthenticatedUser, DbSession
from medical_api.core.security import require_roles
from medical_api.modules.identity.repository import (
    InviteRepository,
    PasswordResetRepository,
    RefreshTokenRepository,
    UserRepository,
)
from medical_api.modules.identity.schemas import (
    InviteAcceptRequest,
    InviteCreate,
    InviteCreateResponse,
    LoginRequest,
    LogoutRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    PasswordResetRequestResponse,
    RefreshRequest,
    RegisterOrganizationRequest,
    RegisterOrganizationResponse,
    TokenResponse,
    UserRead,
)
from medical_api.modules.identity.service import AuthService

router = APIRouter()


def _build_service(session: AsyncSession) -> AuthService:
    return AuthService(
        session,
        UserRepository(session),
        RefreshTokenRepository(session),
        InviteRepository(session),
        PasswordResetRepository(session),
    )


@router.post("/register-organization", response_model=RegisterOrganizationResponse, status_code=201)
async def register_organization(
    payload: RegisterOrganizationRequest, session: DbSession
) -> RegisterOrganizationResponse:
    """Bootstraps a new clinic: creates the organization and its first
    organization_admin user in one call. Every subsequent user is created
    via an invite (see /invites) so it always has an inviting admin.
    """
    service = _build_service(session)
    organization, tokens = await service.register_organization(payload)
    await session.commit()
    return RegisterOrganizationResponse(organization_id=organization.id, **tokens.model_dump())


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest, organization_id: uuid.UUID, session: DbSession
) -> TokenResponse:
    service = _build_service(session)
    tokens = await service.login(organization_id, payload.email, payload.password)
    await session.commit()
    return tokens


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, session: DbSession) -> TokenResponse:
    service = _build_service(session)
    tokens = await service.refresh(payload.refresh_token)
    await session.commit()
    return tokens


@router.post("/logout", status_code=204)
async def logout(payload: LogoutRequest, session: DbSession) -> None:
    service = _build_service(session)
    await service.logout(payload.refresh_token)
    await session.commit()


@router.get("/me", response_model=UserRead)
async def get_me(user: AuthenticatedUser, session: DbSession) -> UserRead:
    repository = UserRepository(session)
    db_user = await repository.get_by_id(user.user_id)
    if db_user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    roles = await repository.get_roles(user.user_id)
    return UserRead(
        id=db_user.id,
        organization_id=db_user.organization_id,
        email=db_user.email,
        full_name=db_user.full_name,
        roles=roles,
    )


@router.post(
    "/invites",
    response_model=InviteCreateResponse,
    status_code=201,
    dependencies=[Depends(require_roles("organization_admin", "platform_admin"))],
)
async def create_invite(
    payload: InviteCreate, user: AuthenticatedUser, session: DbSession
) -> InviteCreateResponse:
    service = _build_service(session)
    invite, raw_token = await service.create_invite(
        user.organization_id, user.user_id, payload.email, payload.role
    )
    await session.commit()
    return InviteCreateResponse(invite_id=invite.id, token=raw_token)


@router.post("/invites/{token}/accept", response_model=TokenResponse, status_code=201)
async def accept_invite(
    token: str, payload: InviteAcceptRequest, session: DbSession
) -> TokenResponse:
    service = _build_service(session)
    tokens = await service.accept_invite(token, payload.full_name, payload.password)
    await session.commit()
    return tokens


@router.post("/password-reset/request", response_model=PasswordResetRequestResponse)
async def request_password_reset(
    payload: PasswordResetRequest, session: DbSession
) -> PasswordResetRequestResponse:
    service = _build_service(session)
    raw_token = await service.request_password_reset(payload.organization_id, payload.email)
    await session.commit()
    # Same response shape regardless of whether the account exists — only
    # `token` differs, and that field is dev-mode only (see schema note).
    return PasswordResetRequestResponse(
        detail="If that account exists, a reset link has been sent.", token=raw_token
    )


@router.post("/password-reset/confirm", status_code=204)
async def confirm_password_reset(payload: PasswordResetConfirm, session: DbSession) -> None:
    service = _build_service(session)
    await service.reset_password(payload.token, payload.new_password)
    await session.commit()
