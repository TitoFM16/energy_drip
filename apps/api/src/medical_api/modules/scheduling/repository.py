import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from medical_api.modules.scheduling.models import Appointment, AppointmentStatusHistory


class AppointmentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(
        self, organization_id: uuid.UUID, appointment_id: uuid.UUID
    ) -> Appointment | None:
        stmt = select(Appointment).where(
            Appointment.organization_id == organization_id, Appointment.id == appointment_id
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_by_id(self, appointment_id: uuid.UUID) -> Appointment | None:
        """Unscoped lookup for trusted internal callers (the worker), which
        operate across organizations rather than on behalf of one user.
        """
        return await self.session.get(Appointment, appointment_id)

    async def list_for_range(
        self, organization_id: uuid.UUID, start: datetime, end: datetime
    ) -> list[Appointment]:
        stmt = (
            select(Appointment)
            .where(
                Appointment.organization_id == organization_id,
                Appointment.starts_at >= start,
                Appointment.starts_at < end,
            )
            .order_by(Appointment.starts_at)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def has_conflict(
        self, practitioner_id: uuid.UUID, starts_at: datetime, ends_at: datetime
    ) -> bool:
        stmt = select(Appointment.id).where(
            Appointment.practitioner_id == practitioner_id,
            Appointment.status.notin_(["cancelled", "no_show"]),
            Appointment.starts_at < ends_at,
            Appointment.ends_at > starts_at,
        )
        return (await self.session.execute(stmt)).first() is not None

    async def create(self, appointment: Appointment) -> Appointment:
        self.session.add(appointment)
        await self.session.flush()
        return appointment

    async def add_status_history(self, entry: AppointmentStatusHistory) -> None:
        self.session.add(entry)
        await self.session.flush()
