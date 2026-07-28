import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from medical_api.modules.scheduling.models import (
    Appointment,
    AppointmentStatus,
    AppointmentStatusHistory,
    AvailabilityRule,
)

_INACTIVE_STATUSES = (AppointmentStatus.CANCELLED, AppointmentStatus.NO_SHOW)


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
            Appointment.status.notin_(_INACTIVE_STATUSES),
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

    async def list_for_practitioner_range(
        self, practitioner_id: uuid.UUID, start: datetime, end: datetime
    ) -> list[Appointment]:
        """Busy periods for slot computation: any non-cancelled appointment
        overlapping [start, end), regardless of which patient it's for.
        """
        stmt = select(Appointment).where(
            Appointment.practitioner_id == practitioner_id,
            Appointment.status.notin_(_INACTIVE_STATUSES),
            Appointment.starts_at < end,
            Appointment.ends_at > start,
        )
        return list((await self.session.execute(stmt)).scalars().all())


class AvailabilityRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_rule(self, rule: AvailabilityRule) -> AvailabilityRule:
        self.session.add(rule)
        await self.session.flush()
        return rule

    async def list_rules(
        self, organization_id: uuid.UUID, practitioner_id: uuid.UUID
    ) -> list[AvailabilityRule]:
        stmt = select(AvailabilityRule).where(
            AvailabilityRule.organization_id == organization_id,
            AvailabilityRule.practitioner_id == practitioner_id,
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_rule(
        self, organization_id: uuid.UUID, rule_id: uuid.UUID
    ) -> AvailabilityRule | None:
        stmt = select(AvailabilityRule).where(
            AvailabilityRule.organization_id == organization_id, AvailabilityRule.id == rule_id
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def delete_rule(self, rule: AvailabilityRule) -> None:
        await self.session.delete(rule)
        await self.session.flush()
