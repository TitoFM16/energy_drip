import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from medical_api.modules.treatments.models import TreatmentPlan, TreatmentSession


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
