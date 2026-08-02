from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from medical_api.modules.organizations.models import Organization


class OrganizationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def exists_any(self) -> bool:
        stmt = select(func.count()).select_from(Organization)
        count = (await self.session.execute(stmt)).scalar_one()
        return count > 0

    async def get_first(self) -> Organization | None:
        """This product has exactly one organization — see the single-clinic
        scope decision in docs/missing_features.md — so callers that just
        need "the" organization (rather than one scoped to a specific user)
        can use this instead of requiring an explicit ID.
        """
        stmt = select(Organization).order_by(Organization.created_at).limit(1)
        return (await self.session.execute(stmt)).scalar_one_or_none()
