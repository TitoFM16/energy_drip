import uuid
from datetime import UTC, datetime

from medical_api.core.exceptions import NotFoundError
from medical_api.modules.treatments.models import TreatmentPlan, TreatmentSession
from medical_api.modules.treatments.repository import TreatmentRepository
from medical_api.modules.treatments.schemas import TreatmentPlanCreate, TreatmentSessionCreate


class TreatmentService:
    def __init__(self, repository: TreatmentRepository):
        self.repository = repository

    async def create_plan(
        self, organization_id: uuid.UUID, data: TreatmentPlanCreate
    ) -> TreatmentPlan:
        plan = TreatmentPlan(organization_id=organization_id, **data.model_dump())
        return await self.repository.create_plan(plan)

    async def get_plan(self, organization_id: uuid.UUID, plan_id: uuid.UUID) -> TreatmentPlan:
        plan = await self.repository.get_plan(organization_id, plan_id)
        if plan is None:
            raise NotFoundError("TreatmentPlan", plan_id)
        return plan

    async def record_session(
        self, organization_id: uuid.UUID, data: TreatmentSessionCreate
    ) -> TreatmentSession:
        await self.get_plan(organization_id, data.treatment_plan_id)
        session_row = TreatmentSession(performed_at=datetime.now(UTC), **data.model_dump())
        return await self.repository.create_session(session_row)
