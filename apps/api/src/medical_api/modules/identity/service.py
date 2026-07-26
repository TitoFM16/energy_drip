import uuid

from fastapi import HTTPException, status

from medical_api.core.security import create_access_token, verify_password
from medical_api.modules.identity.repository import UserRepository
from medical_api.modules.identity.schemas import TokenResponse


class AuthService:
    def __init__(self, repository: UserRepository):
        self.repository = repository

    async def login(self, organization_id: uuid.UUID, email: str, password: str) -> TokenResponse:
        user = await self.repository.get_by_email(organization_id, email)
        if (
            user is None
            or not user.is_active
            or not verify_password(password, user.hashed_password)
        ):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
        roles = await self.repository.get_roles(user.id)
        token = create_access_token(
            subject=str(user.id),
            extra_claims={"organization_id": str(user.organization_id), "roles": roles},
        )
        return TokenResponse(access_token=token)
