import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from medical_api.core.exceptions import ConflictError, NotFoundError
from medical_api.modules.notifications.service import enqueue_event
from medical_api.modules.scheduling.models import (
    Appointment,
    AppointmentStatus,
    AppointmentStatusHistory,
)
from medical_api.modules.scheduling.repository import AppointmentRepository
from medical_api.modules.scheduling.schemas import AppointmentCreate


class AppointmentService:
    def __init__(self, repository: AppointmentRepository, session: AsyncSession):
        self.repository = repository
        self.session = session

    async def schedule(self, organization_id: uuid.UUID, data: AppointmentCreate) -> Appointment:
        if await self.repository.has_conflict(data.practitioner_id, data.starts_at, data.ends_at):
            raise ConflictError("Practitioner already has an appointment in that time range")

        appointment = Appointment(organization_id=organization_id, **data.model_dump())
        await self.repository.create(appointment)
        await self.repository.add_status_history(
            AppointmentStatusHistory(
                appointment_id=appointment.id, from_status=None, to_status=appointment.status
            )
        )
        # Same transaction as the appointment write: outbox guarantees the
        # worker eventually sends confirmation + consent link even if the
        # notification provider is down right now.
        await enqueue_event(
            self.session,
            organization_id=organization_id,
            event_type="appointment.scheduled",
            payload={
                "appointment_id": str(appointment.id),
                "patient_id": str(appointment.patient_id),
            },
        )
        return appointment

    async def change_status(
        self,
        organization_id: uuid.UUID,
        appointment_id: uuid.UUID,
        new_status: AppointmentStatus,
        reason: str | None,
    ) -> Appointment:
        appointment = await self.repository.get(organization_id, appointment_id)
        if appointment is None:
            raise NotFoundError("Appointment", appointment_id)
        previous_status = appointment.status
        appointment.status = new_status
        await self.repository.add_status_history(
            AppointmentStatusHistory(
                appointment_id=appointment.id,
                from_status=previous_status,
                to_status=new_status,
                reason=reason,
            )
        )
        if new_status == AppointmentStatus.CANCELLED:
            await enqueue_event(
                self.session,
                organization_id=organization_id,
                event_type="appointment.cancelled",
                payload={"appointment_id": str(appointment.id)},
            )
        return appointment
