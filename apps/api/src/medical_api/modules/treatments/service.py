import uuid
from datetime import UTC, datetime

from medical_api.core.exceptions import NotFoundError
from medical_api.modules.treatments.models import (
    TreatmentDefinition,
    TreatmentPlan,
    TreatmentSession,
)
from medical_api.modules.treatments.repository import (
    TreatmentDefinitionRepository,
    TreatmentRepository,
)
from medical_api.modules.treatments.schemas import (
    TreatmentDefinitionCreate,
    TreatmentDefinitionUpdate,
    TreatmentPlanCreate,
    TreatmentPlanUpdate,
    TreatmentSessionCreate,
)


class TreatmentDefinitionService:
    def __init__(self, repository: TreatmentDefinitionRepository):
        self.repository = repository

    async def create(
        self, organization_id: uuid.UUID, data: TreatmentDefinitionCreate
    ) -> TreatmentDefinition:
        definition = TreatmentDefinition(organization_id=organization_id, **data.model_dump())
        return await self.repository.create(definition)

    async def list_all(
        self, organization_id: uuid.UUID, include_inactive: bool = False
    ) -> list[TreatmentDefinition]:
        return await self.repository.list_all(organization_id, include_inactive)

    async def update(
        self, organization_id: uuid.UUID, definition_id: uuid.UUID, data: TreatmentDefinitionUpdate
    ) -> TreatmentDefinition:
        definition = await self.repository.get(organization_id, definition_id)
        if definition is None:
            raise NotFoundError("TreatmentDefinition", definition_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(definition, field, value)
        return definition


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

    async def list_plans_for_patient(
        self, organization_id: uuid.UUID, patient_id: uuid.UUID
    ) -> list[TreatmentPlan]:
        return await self.repository.list_plans_for_patient(organization_id, patient_id)

    async def update_plan(
        self, organization_id: uuid.UUID, plan_id: uuid.UUID, data: TreatmentPlanUpdate
    ) -> TreatmentPlan:
        plan = await self.get_plan(organization_id, plan_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(plan, field, value)
        return plan

    async def record_session(
        self, organization_id: uuid.UUID, data: TreatmentSessionCreate
    ) -> TreatmentSession:
        await self.get_plan(organization_id, data.treatment_plan_id)
        session_row = TreatmentSession(performed_at=datetime.now(UTC), **data.model_dump())
        return await self.repository.create_session(session_row)
