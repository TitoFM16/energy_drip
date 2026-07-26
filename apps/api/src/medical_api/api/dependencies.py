from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from medical_api.core.database import get_db
from medical_api.core.security import CurrentUser, get_current_user

DbSession = Annotated[AsyncSession, Depends(get_db)]
AuthenticatedUser = Annotated[CurrentUser, Depends(get_current_user)]


async def get_request_scope(user: AuthenticatedUser) -> AsyncIterator[CurrentUser]:
    """Yields the current user, scoped for downstream org-boundary checks."""
    yield user
