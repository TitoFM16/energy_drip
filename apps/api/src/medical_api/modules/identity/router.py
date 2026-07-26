import uuid

from fastapi import APIRouter, HTTPException, status

from medical_api.api.dependencies import AuthenticatedUser, DbSession
from medical_api.modules.identity.repository import UserRepository
from medical_api.modules.identity.schemas import LoginRequest, TokenResponse, UserRead
from medical_api.modules.identity.service import AuthService

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest, organization_id: uuid.UUID, session: DbSession
) -> TokenResponse:
    service = AuthService(UserRepository(session))
    return await service.login(organization_id, payload.email, payload.password)


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
