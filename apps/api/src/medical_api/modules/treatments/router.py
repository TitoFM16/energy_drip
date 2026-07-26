import uuid

from fastapi import APIRouter, Depends

from medical_api.api.dependencies import AuthenticatedUser, DbSession
from medical_api.core.security import require_roles
from medical_api.modules.treatments.repository import TreatmentRepository
from medical_api.modules.treatments.schemas import (
    TreatmentPlanCreate,
    TreatmentPlanRead,
    TreatmentSessionCreate,
    TreatmentSessionRead,
)
from medical_api.modules.treatments.service import TreatmentService

router = APIRouter()


@router.post(
    "/plans",
    response_model=TreatmentPlanRead,
    status_code=201,
    dependencies=[Depends(require_roles("practitioner", "medical_director"))],
)
async def create_treatment_plan(
    payload: TreatmentPlanCreate, user: AuthenticatedUser, session: DbSession
) -> TreatmentPlanRead:
    service = TreatmentService(TreatmentRepository(session))
    plan = await service.create_plan(user.organization_id, payload)
    await session.commit()
    return plan


@router.get("/plans/{plan_id}", response_model=TreatmentPlanRead)
async def get_treatment_plan(
    plan_id: uuid.UUID, user: AuthenticatedUser, session: DbSession
) -> TreatmentPlanRead:
    service = TreatmentService(TreatmentRepository(session))
    return await service.get_plan(user.organization_id, plan_id)


@router.get("/plans/{plan_id}/sessions", response_model=list[TreatmentSessionRead])
async def list_treatment_sessions(
    plan_id: uuid.UUID, user: AuthenticatedUser, session: DbSession
) -> list[TreatmentSessionRead]:
    repository = TreatmentRepository(session)
    return await repository.list_sessions_for_plan(plan_id)


@router.post(
    "/sessions",
    response_model=TreatmentSessionRead,
    status_code=201,
    dependencies=[Depends(require_roles("practitioner", "medical_director"))],
)
async def record_treatment_session(
    payload: TreatmentSessionCreate, user: AuthenticatedUser, session: DbSession
) -> TreatmentSessionRead:
    service = TreatmentService(TreatmentRepository(session))
    treatment_session = await service.record_session(user.organization_id, payload)
    await session.commit()
    return treatment_session
