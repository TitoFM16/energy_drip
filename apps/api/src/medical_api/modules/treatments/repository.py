import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from medical_api.modules.treatments.models import (
    TreatmentDefinition,
    TreatmentPlan,
    TreatmentSession,
)


class TreatmentDefinitionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, definition: TreatmentDefinition) -> TreatmentDefinition:
        self.session.add(definition)
        await self.session.flush()
        return definition

    async def get(
        self, organization_id: uuid.UUID, definition_id: uuid.UUID
    ) -> TreatmentDefinition | None:
        stmt = select(TreatmentDefinition).where(
            TreatmentDefinition.organization_id == organization_id,
            TreatmentDefinition.id == definition_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_all(
        self, organization_id: uuid.UUID, include_inactive: bool = False
    ) -> list[TreatmentDefinition]:
        conditions = [TreatmentDefinition.organization_id == organization_id]
        if not include_inactive:
            conditions.append(TreatmentDefinition.is_active.is_(True))
        stmt = select(TreatmentDefinition).where(*conditions).order_by(TreatmentDefinition.name)
        return list((await self.session.execute(stmt)).scalars().all())


class TreatmentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_plan(
        self, organization_id: uuid.UUID, plan_id: uuid.UUID
    ) -> TreatmentPlan | None:
        stmt = select(TreatmentPlan).where(
            TreatmentPlan.organization_id == organization_id, TreatmentPlan.id == plan_id
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_plans_for_patient(
        self, organization_id: uuid.UUID, patient_id: uuid.UUID
    ) -> list[TreatmentPlan]:
        stmt = select(TreatmentPlan).where(
            TreatmentPlan.organization_id == organization_id, TreatmentPlan.patient_id == patient_id
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def create_plan(self, plan: TreatmentPlan) -> TreatmentPlan:
        self.session.add(plan)
        await self.session.flush()
        return plan

    async def list_sessions_for_plan(self, treatment_plan_id: uuid.UUID) -> list[TreatmentSession]:
        stmt = (
            select(TreatmentSession)
            .where(TreatmentSession.treatment_plan_id == treatment_plan_id)
            .order_by(TreatmentSession.session_number)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def create_session(self, session_row: TreatmentSession) -> TreatmentSession:
        self.session.add(session_row)
        await self.session.flush()
        return session_row
