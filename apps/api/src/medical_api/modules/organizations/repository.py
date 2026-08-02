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
