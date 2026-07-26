import uuid
from datetime import datetime

from fastapi import APIRouter, Depends

from medical_api.api.dependencies import AuthenticatedUser, DbSession
from medical_api.core.security import require_roles
from medical_api.modules.scheduling.repository import AppointmentRepository
from medical_api.modules.scheduling.schemas import (
    AppointmentCreate,
    AppointmentRead,
    AppointmentStatusUpdate,
)
from medical_api.modules.scheduling.service import AppointmentService

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
