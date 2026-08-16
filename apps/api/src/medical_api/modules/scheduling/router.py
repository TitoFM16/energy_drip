import uuid
from datetime import date, datetime

from fastapi import APIRouter, Depends, Query

from medical_api.api.dependencies import AuthenticatedUser, DbSession
from medical_api.core.security import require_roles
from medical_api.modules.audit.service import AuditService
from medical_api.modules.identity.repository import UserRepository
from medical_api.modules.scheduling.repository import (
    AppointmentRepository,
    AvailabilityRepository,
    PractitionerRepository,
)
from medical_api.modules.scheduling.schemas import (
    AppointmentCreate,
    AppointmentRead,
    AppointmentReschedule,
    AppointmentStatusHistoryRead,
    AppointmentStatusUpdate,
    AvailabilityRuleCreate,
    AvailabilityRuleRead,
    AvailableSlot,
    PractitionerCreate,
    PractitionerRead,
    PractitionerUpdate,
)
from medical_api.modules.scheduling.service import (
    AppointmentService,
    AvailabilityService,
    PractitionerService,
)

# Mounted at /api/v1/appointments (this router) and /api/v1/practitioners
# (practitioners_router) — practitioners live in the scheduling module
# because that's where their only current use (availability/booking) is,
# but they're not sub-resources of appointments.
router = APIRouter()
practitioners_router = APIRouter()


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
    appointment = await service.schedule(user.organization_id, payload, actor_user_id=user.user_id)
    await AuditService(session).record(
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        action="appointment.created",
        resource_type="appointment",
        resource_id=str(appointment.id),
        metadata={"patient_id": str(appointment.patient_id)},
    )
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
        user.organization_id,
        appointment_id,
        payload.status,
        payload.reason,
        actor_user_id=user.user_id,
    )
    await AuditService(session).record(
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        action="appointment.status_changed",
        resource_type="appointment",
        resource_id=str(appointment.id),
        metadata={"status": str(payload.status), "reason": payload.reason},
    )
    await session.commit()
    return appointment


@router.patch(
    "/{appointment_id}/reschedule",
    response_model=AppointmentRead,
    dependencies=[
        Depends(require_roles("receptionist", "assistant", "practitioner", "organization_admin"))
    ],
)
async def reschedule_appointment(
    appointment_id: uuid.UUID,
    payload: AppointmentReschedule,
    user: AuthenticatedUser,
    session: DbSession,
) -> AppointmentRead:
    service = AppointmentService(AppointmentRepository(session), session)
    # Same identity-mapped object will be mutated in place by reschedule(),
    # so the old times must be captured as plain strings now — reading
    # `previous.starts_at` again after the call would already see the new
    # value since it's the same ORM instance, not a separate snapshot.
    previous = await service.repository.get(user.organization_id, appointment_id)
    previous_starts_at = previous.starts_at.isoformat() if previous else None
    previous_ends_at = previous.ends_at.isoformat() if previous else None
    appointment = await service.reschedule(
        user.organization_id, appointment_id, payload.starts_at, payload.ends_at
    )
    await AuditService(session).record(
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        action="appointment.rescheduled",
        resource_type="appointment",
        resource_id=str(appointment.id),
        metadata={
            "previous_starts_at": previous_starts_at,
            "previous_ends_at": previous_ends_at,
            "starts_at": appointment.starts_at.isoformat(),
            "ends_at": appointment.ends_at.isoformat(),
        },
    )
    await session.commit()
    return appointment


@router.get("/{appointment_id}/status-history", response_model=list[AppointmentStatusHistoryRead])
async def get_appointment_status_history(
    appointment_id: uuid.UUID, user: AuthenticatedUser, session: DbSession
) -> list[AppointmentStatusHistoryRead]:
    service = AppointmentService(AppointmentRepository(session), session)
    return await service.get_status_history(user.organization_id, appointment_id)


@router.get("/availability", response_model=list[AvailableSlot])
async def get_available_slots(
    user: AuthenticatedUser,
    session: DbSession,
    practitioner_id: uuid.UUID,
    date_from: date,
    date_to: date,
    # A duration <= 0 makes AvailabilityService.compute_slots' slot-walking
    # loop never advance past a day's end, hanging the process — see
    # missing_features.md's "Appointment management" for the full writeup.
    duration_minutes: int = Query(30, ge=5, le=480),
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
    await AuditService(session).record(
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        action="availability_rule.created",
        resource_type="availability_rule",
        resource_id=str(rule.id),
        metadata={"practitioner_id": str(rule.practitioner_id)},
    )
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
    await AuditService(session).record(
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        action="availability_rule.deleted",
        resource_type="availability_rule",
        resource_id=str(rule_id),
    )
    await session.commit()


@practitioners_router.post(
    "",
    response_model=PractitionerRead,
    status_code=201,
    dependencies=[Depends(require_roles("organization_admin", "medical_director"))],
)
async def create_practitioner(
    payload: PractitionerCreate, user: AuthenticatedUser, session: DbSession
) -> PractitionerRead:
    service = PractitionerService(PractitionerRepository(session), UserRepository(session))
    practitioner = await service.create(user.organization_id, payload)
    await AuditService(session).record(
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        action="practitioner.created",
        resource_type="practitioner",
        resource_id=str(practitioner.id),
    )
    await session.commit()
    return practitioner


@practitioners_router.get("", response_model=list[PractitionerRead])
async def list_practitioners(
    user: AuthenticatedUser, session: DbSession, include_inactive: bool = False
) -> list[PractitionerRead]:
    service = PractitionerService(PractitionerRepository(session), UserRepository(session))
    return await service.list_active(user.organization_id, include_inactive)


@practitioners_router.patch(
    "/{practitioner_id}",
    response_model=PractitionerRead,
    dependencies=[Depends(require_roles("organization_admin", "medical_director"))],
)
async def update_practitioner(
    practitioner_id: uuid.UUID,
    payload: PractitionerUpdate,
    user: AuthenticatedUser,
    session: DbSession,
) -> PractitionerRead:
    service = PractitionerService(PractitionerRepository(session), UserRepository(session))
    practitioner = await service.update(user.organization_id, practitioner_id, payload)
    await AuditService(session).record(
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        action="practitioner.updated",
        resource_type="practitioner",
        resource_id=str(practitioner.id),
        metadata={"fields": sorted(payload.model_dump(exclude_unset=True).keys())},
    )
    await session.commit()
    return practitioner
