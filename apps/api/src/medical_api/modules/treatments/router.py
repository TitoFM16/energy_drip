import uuid

from fastapi import APIRouter, Depends

from medical_api.api.dependencies import AuthenticatedUser, DbSession
from medical_api.core.security import require_roles
from medical_api.modules.treatments.repository import (
    TreatmentDefinitionRepository,
    TreatmentRepository,
)
from medical_api.modules.treatments.schemas import (
    TreatmentDefinitionCreate,
    TreatmentDefinitionRead,
    TreatmentDefinitionUpdate,
    TreatmentPlanCreate,
    TreatmentPlanRead,
    TreatmentPlanUpdate,
    TreatmentSessionCreate,
    TreatmentSessionRead,
)
from medical_api.modules.treatments.service import TreatmentDefinitionService, TreatmentService

router = APIRouter()


@router.post(
    "/definitions",
    response_model=TreatmentDefinitionRead,
    status_code=201,
    dependencies=[Depends(require_roles("organization_admin", "medical_director"))],
)
async def create_treatment_definition(
    payload: TreatmentDefinitionCreate, user: AuthenticatedUser, session: DbSession
) -> TreatmentDefinitionRead:
    service = TreatmentDefinitionService(TreatmentDefinitionRepository(session))
    definition = await service.create(user.organization_id, payload)
    await session.commit()
    return definition


@router.get("/definitions", response_model=list[TreatmentDefinitionRead])
async def list_treatment_definitions(
    user: AuthenticatedUser, session: DbSession, include_inactive: bool = False
) -> list[TreatmentDefinitionRead]:
    service = TreatmentDefinitionService(TreatmentDefinitionRepository(session))
    return await service.list_all(user.organization_id, include_inactive)


@router.patch(
    "/definitions/{definition_id}",
    response_model=TreatmentDefinitionRead,
    dependencies=[Depends(require_roles("organization_admin", "medical_director"))],
)
async def update_treatment_definition(
    definition_id: uuid.UUID,
    payload: TreatmentDefinitionUpdate,
    user: AuthenticatedUser,
    session: DbSession,
) -> TreatmentDefinitionRead:
    service = TreatmentDefinitionService(TreatmentDefinitionRepository(session))
    definition = await service.update(user.organization_id, definition_id, payload)
    await session.commit()
    return definition


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


@router.get("/plans", response_model=list[TreatmentPlanRead])
async def list_treatment_plans(
    user: AuthenticatedUser, session: DbSession, patient_id: uuid.UUID
) -> list[TreatmentPlanRead]:
    service = TreatmentService(TreatmentRepository(session))
    return await service.list_plans_for_patient(user.organization_id, patient_id)


@router.get("/plans/{plan_id}", response_model=TreatmentPlanRead)
async def get_treatment_plan(
    plan_id: uuid.UUID, user: AuthenticatedUser, session: DbSession
) -> TreatmentPlanRead:
    service = TreatmentService(TreatmentRepository(session))
    return await service.get_plan(user.organization_id, plan_id)


@router.patch(
    "/plans/{plan_id}",
    response_model=TreatmentPlanRead,
    dependencies=[Depends(require_roles("practitioner", "medical_director"))],
)
async def update_treatment_plan(
    plan_id: uuid.UUID, payload: TreatmentPlanUpdate, user: AuthenticatedUser, session: DbSession
) -> TreatmentPlanRead:
    service = TreatmentService(TreatmentRepository(session))
    plan = await service.update_plan(user.organization_id, plan_id, payload)
    await session.commit()
    return plan


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
