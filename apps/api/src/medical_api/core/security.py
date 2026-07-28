import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from medical_api.core.config import get_settings

settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

# bcrypt's own C extension rejects secrets over 72 bytes outright (no silent
# truncation) — schemas enforce this as a request-validation error via
# Field(max_length=72) so it never reaches here as a raw crash.


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def create_access_token(subject: str, extra_claims: dict[str, Any] | None = None) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] = {"sub": subject, "exp": expire}
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


class CurrentUser:
    def __init__(self, user_id: uuid.UUID, organization_id: uuid.UUID, roles: list[str]):
        self.user_id = user_id
        self.organization_id = organization_id
        self.roles = roles

    def has_role(self, *roles: str) -> bool:
        return any(role in self.roles for role in roles)


async def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
) -> CurrentUser:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token is None:
        raise unauthorized
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id = payload.get("sub")
        organization_id = payload.get("organization_id")
        if user_id is None or organization_id is None:
            raise unauthorized
    except JWTError as exc:
        raise unauthorized from exc
    return CurrentUser(
        user_id=uuid.UUID(user_id),
        organization_id=uuid.UUID(organization_id),
        roles=payload.get("roles", []),
    )


def require_roles(*roles: str):
    async def _check(user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
        if not user.has_role(*roles):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
        return user

    return _check
