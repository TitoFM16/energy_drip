import uuid
from datetime import date, datetime

from fastapi import APIRouter, Depends

from medical_api.api.dependencies import AuthenticatedUser, DbSession
from medical_api.core.security import require_roles
from medical_api.modules.scheduling.repository import AppointmentRepository, AvailabilityRepository
from medical_api.modules.scheduling.schemas import (
    AppointmentCreate,
    AppointmentRead,
    AppointmentStatusUpdate,
    AvailabilityRuleCreate,
    AvailabilityRuleRead,
    AvailableSlot,
)
from medical_api.modules.scheduling.service import AppointmentService, AvailabilityService

router = APIRouter()


@router.get("", response_model=list[AppointmentRead])
async def list_appointments(
    user: AuthenticatedUser, session: DbSession, start: datetime, end: datetime
) -> list[AppointmentRead]:
    repository = AppointmentRepository(session)
    return await repository.list_for_range(user.organization_id, start, end)


@router.post(
    "",
    response_model=AppointmentRead,
    status_code=201,
    dependencies=[
        Depends(require_roles("receptionist", "assistant", "practitioner", "organization_admin"))
    ],
)
async def create_appointment(
    payload: AppointmentCreate, user: AuthenticatedUser, session: DbSession
) -> AppointmentRead:
    service = AppointmentService(AppointmentRepository(session), session)
    appointment = await service.schedule(user.organization_id, payload)
    await session.commit()
    return appointment


@router.post("/{appointment_id}/status", response_model=AppointmentRead)
async def update_appointment_status(
    appointment_id: uuid.UUID,
    payload: AppointmentStatusUpdate,
    user: AuthenticatedUser,
    session: DbSession,
) -> AppointmentRead:
    service = AppointmentService(AppointmentRepository(session), session)
    appointment = await service.change_status(
        user.organization_id, appointment_id, payload.status, payload.reason
    )
    await session.commit()
    return appointment


@router.get("/availability", response_model=list[AvailableSlot])
async def get_available_slots(
    user: AuthenticatedUser,
    session: DbSession,
    practitioner_id: uuid.UUID,
    date_from: date,
    date_to: date,
    duration_minutes: int = 30,
) -> list[AvailableSlot]:
    service = AvailabilityService(AvailabilityRepository(session), AppointmentRepository(session))
    return await service.compute_slots(
        user.organization_id, practitioner_id, date_from, date_to, duration_minutes
    )


@router.post(
    "/availability-rules",
    response_model=AvailabilityRuleRead,
    status_code=201,
    dependencies=[Depends(require_roles("practitioner", "organization_admin", "medical_director"))],
)
async def create_availability_rule(
    payload: AvailabilityRuleCreate, user: AuthenticatedUser, session: DbSession
) -> AvailabilityRuleRead:
    service = AvailabilityService(AvailabilityRepository(session), AppointmentRepository(session))
    rule = await service.create_rule(user.organization_id, payload)
    await session.commit()
    return rule


@router.get("/availability-rules", response_model=list[AvailabilityRuleRead])
async def list_availability_rules(
    user: AuthenticatedUser, session: DbSession, practitioner_id: uuid.UUID
) -> list[AvailabilityRuleRead]:
    repository = AvailabilityRepository(session)
    return await repository.list_rules(user.organization_id, practitioner_id)


@router.delete(
    "/availability-rules/{rule_id}",
    status_code=204,
    dependencies=[Depends(require_roles("practitioner", "organization_admin", "medical_director"))],
)
async def delete_availability_rule(
    rule_id: uuid.UUID, user: AuthenticatedUser, session: DbSession
) -> None:
    service = AvailabilityService(AvailabilityRepository(session), AppointmentRepository(session))
    await service.delete_rule(user.organization_id, rule_id)
    await session.commit()
