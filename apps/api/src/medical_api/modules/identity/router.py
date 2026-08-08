import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from medical_api.api.dependencies import AuthenticatedUser, DbSession
from medical_api.core.config import get_settings
from medical_api.core.exceptions import RateLimitedError
from medical_api.core.rate_limit import check_rate_limit
from medical_api.core.request_context import get_ip_address
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
    UserRolesUpdate,
)
from medical_api.modules.identity.service import AuthService

router = APIRouter()
settings = get_settings()

# All four keyed by IP, same fixed-window approach as the public booking
# form (see check_rate_limit's docstring) — these are the other endpoints
# an unauthenticated caller can hammer to brute-force a password or guess a
# single-use token. Limits are generous enough that a real user mistyping a
# password or clicking a stale link a few times never notices, but tight
# enough to slow down automated guessing.
#
# Login's limit specifically had to be raised from an initial, tighter 10 —
# every E2E spec logs in through the real form (not a token injected into
# storage), so a full suite run alone is ~10 real logins from the one
# runner IP, and CI retries a failed spec once (playwright.config.ts). A
# small shared-office clinic behind one NAT'd IP has the same shape of
# problem in production. This is a per-IP soft limit, not per-account
# lockout — meaningfully slows automated guessing without risking a whole
# office (or a CI run) getting locked out by ordinary concurrent use.
_LOGIN_RATE_LIMIT = 30
_LOGIN_RATE_WINDOW_SECONDS = 300
# Same headroom reasoning as login above: every E2E spec's bootstrapClinic
# accepts one invite, so a single suite run is already ~10 real calls from
# one IP, and a couple of manual reruns within the same hour (routine while
# developing) stack on top of each other since this window is much longer
# than login's. An initial 20/hour looked generous in isolation but wasn't
# once measured against actual repeated local verification.
_INVITE_ACCEPT_RATE_LIMIT = 60
_INVITE_ACCEPT_RATE_WINDOW_SECONDS = 3600
_PASSWORD_RESET_REQUEST_RATE_LIMIT = 5
_PASSWORD_RESET_REQUEST_RATE_WINDOW_SECONDS = 3600
_PASSWORD_RESET_CONFIRM_RATE_LIMIT = 20
_PASSWORD_RESET_CONFIRM_RATE_WINDOW_SECONDS = 3600


async def _enforce_rate_limit(key: str, *, limit: int, window_seconds: int) -> None:
    allowed = await check_rate_limit(key, limit=limit, window_seconds=window_seconds)
    if not allowed:
        raise RateLimitedError("Too many attempts. Please try again later.")


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
    """One-time bootstrap for this product's single clinic: creates the
    organization and its first organization_admin user together. Every
    subsequent user is created via an invite (see /invites) so it always has
    an inviting admin.

    This product is single-tenant — there is exactly one clinic, ever — so
    this route must never be reachable in production; a production
    deployment is bootstrapped once via an operator-run seed command
    instead. It stays available in non-production environments so local dev
    and the test suite can create disposable clinics.
    """
    if settings.is_production:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Public organization registration is disabled in production. "
            "Bootstrap the clinic with the operator seed command instead.",
        )
    service = _build_service(session)
    organization, tokens = await service.register_organization(payload)
    await session.commit()
    return RegisterOrganizationResponse(organization_id=organization.id, **tokens.model_dump())


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, session: DbSession) -> TokenResponse:
    await _enforce_rate_limit(
        f"login:{get_ip_address() or 'unknown'}",
        limit=_LOGIN_RATE_LIMIT,
        window_seconds=_LOGIN_RATE_WINDOW_SECONDS,
    )
    service = _build_service(session)
    tokens = await service.login(payload.email, payload.password)
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


@router.get(
    "/users",
    response_model=list[UserRead],
    dependencies=[Depends(require_roles("organization_admin", "medical_director"))],
)
async def list_users(user: AuthenticatedUser, session: DbSession) -> list[UserRead]:
    repository = UserRepository(session)
    users = await repository.list_by_organization(user.organization_id)
    return [
        UserRead(
            id=u.id,
            organization_id=u.organization_id,
            email=u.email,
            full_name=u.full_name,
            roles=await repository.get_roles(u.id),
        )
        for u in users
    ]


@router.patch(
    "/users/{target_user_id}/roles",
    response_model=UserRead,
    dependencies=[Depends(require_roles("organization_admin"))],
)
async def update_user_roles(
    target_user_id: uuid.UUID,
    payload: UserRolesUpdate,
    user: AuthenticatedUser,
    session: DbSession,
) -> UserRead:
    service = _build_service(session)
    target = await service.update_user_roles(
        user.organization_id,
        user.user_id,
        target_user_id,
        payload.roles,
    )
    await session.commit()
    return UserRead(
        id=target.id,
        organization_id=target.organization_id,
        email=target.email,
        full_name=target.full_name,
        roles=await UserRepository(session).get_roles(target.id),
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
    await _enforce_rate_limit(
        f"invite_accept:{get_ip_address() or 'unknown'}",
        limit=_INVITE_ACCEPT_RATE_LIMIT,
        window_seconds=_INVITE_ACCEPT_RATE_WINDOW_SECONDS,
    )
    service = _build_service(session)
    tokens = await service.accept_invite(token, payload.full_name, payload.password)
    await session.commit()
    return tokens


@router.post("/password-reset/request", response_model=PasswordResetRequestResponse)
async def request_password_reset(
    payload: PasswordResetRequest, session: DbSession
) -> PasswordResetRequestResponse:
    await _enforce_rate_limit(
        f"password_reset_request:{get_ip_address() or 'unknown'}",
        limit=_PASSWORD_RESET_REQUEST_RATE_LIMIT,
        window_seconds=_PASSWORD_RESET_REQUEST_RATE_WINDOW_SECONDS,
    )
    service = _build_service(session)
    raw_token = await service.request_password_reset(payload.email)
    await session.commit()
    # Same response shape regardless of whether the account exists — only
    # `token` differs, and that field is dev-mode only (see schema note).
    return PasswordResetRequestResponse(
        detail="If that account exists, a reset link has been sent.", token=raw_token
    )


@router.post("/password-reset/confirm", status_code=204)
async def confirm_password_reset(payload: PasswordResetConfirm, session: DbSession) -> None:
    await _enforce_rate_limit(
        f"password_reset_confirm:{get_ip_address() or 'unknown'}",
        limit=_PASSWORD_RESET_CONFIRM_RATE_LIMIT,
        window_seconds=_PASSWORD_RESET_CONFIRM_RATE_WINDOW_SECONDS,
    )
    service = _build_service(session)
    await service.reset_password(payload.token, payload.new_password)
    await session.commit()
