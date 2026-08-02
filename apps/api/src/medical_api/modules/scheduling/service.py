import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from medical_api.core.exceptions import ConflictError, NotFoundError
from medical_api.modules.identity.repository import UserRepository
from medical_api.modules.notifications.service import enqueue_event
from medical_api.modules.scheduling.models import (
    Appointment,
    AppointmentStatus,
    AppointmentStatusHistory,
    AvailabilityRule,
    Practitioner,
)
from medical_api.modules.scheduling.repository import (
    AppointmentRepository,
    AvailabilityRepository,
    PractitionerRepository,
)
from medical_api.modules.scheduling.schemas import (
    AppointmentCreate,
    AvailabilityRuleCreate,
    AvailableSlot,
    PractitionerCreate,
    PractitionerRead,
    PractitionerUpdate,
)

MAX_AVAILABILITY_WINDOW_DAYS = 31


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


class AvailabilityService:
    """Computes bookable slots from a practitioner's recurring weekly rules
    minus their existing appointments.

    MVP simplification: rule `start_time`/`end_time` are interpreted as UTC
    directly rather than converted from a location's local timezone — fine
    for a single-timezone clinic, but multi-location deployments spanning
    timezones will need that conversion added here.
    """

    def __init__(self, repository: AvailabilityRepository, appointments: AppointmentRepository):
        self.repository = repository
        self.appointments = appointments

    async def create_rule(
        self, organization_id: uuid.UUID, data: AvailabilityRuleCreate
    ) -> AvailabilityRule:
        rule = AvailabilityRule(organization_id=organization_id, **data.model_dump())
        return await self.repository.create_rule(rule)

    async def list_rules(
        self, organization_id: uuid.UUID, practitioner_id: uuid.UUID
    ) -> list[AvailabilityRule]:
        return await self.repository.list_rules(organization_id, practitioner_id)

    async def delete_rule(self, organization_id: uuid.UUID, rule_id: uuid.UUID) -> None:
        rule = await self.repository.get_rule(organization_id, rule_id)
        if rule is None:
            raise NotFoundError("AvailabilityRule", rule_id)
        await self.repository.delete_rule(rule)

    async def compute_slots(
        self,
        organization_id: uuid.UUID,
        practitioner_id: uuid.UUID,
        date_from: date,
        date_to: date,
        duration_minutes: int,
    ) -> list[AvailableSlot]:
        if date_to < date_from:
            raise ConflictError("date_to must not be before date_from")
        if (date_to - date_from).days > MAX_AVAILABILITY_WINDOW_DAYS:
            raise ConflictError(f"Date range cannot exceed {MAX_AVAILABILITY_WINDOW_DAYS} days")

        rules = await self.repository.list_rules(organization_id, practitioner_id)
        rules_by_weekday: dict[int, list[AvailabilityRule]] = {}
        for rule in rules:
            rules_by_weekday.setdefault(rule.weekday, []).append(rule)
        if not rules_by_weekday:
            return []

        range_start = datetime.combine(date_from, datetime.min.time(), tzinfo=UTC)
        range_end = datetime.combine(date_to, datetime.min.time(), tzinfo=UTC) + timedelta(days=1)
        busy_periods = [
            (appointment.starts_at, appointment.ends_at)
            for appointment in await self.appointments.list_for_practitioner_range(
                practitioner_id, range_start, range_end
            )
        ]

        now = datetime.now(UTC)
        step = timedelta(minutes=duration_minutes)
        slots: list[AvailableSlot] = []
        current_day = date_from
        while current_day <= date_to:
            for rule in rules_by_weekday.get(current_day.weekday(), []):
                cursor = datetime.combine(current_day, rule.start_time, tzinfo=UTC)
                day_end = datetime.combine(current_day, rule.end_time, tzinfo=UTC)
                while cursor + step <= day_end:
                    slot_end = cursor + step
                    if cursor >= now and not _overlaps_any(cursor, slot_end, busy_periods):
                        slots.append(AvailableSlot(starts_at=cursor, ends_at=slot_end))
                    cursor += step
            current_day += timedelta(days=1)
        return slots


def _overlaps_any(
    starts_at: datetime, ends_at: datetime, busy_periods: list[tuple[datetime, datetime]]
) -> bool:
    return any(
        starts_at < busy_end and ends_at > busy_start for busy_start, busy_end in busy_periods
    )


class PractitionerService:
    def __init__(self, repository: PractitionerRepository, users: UserRepository):
        self.repository = repository
        self.users = users

    async def _to_read(self, practitioner: Practitioner) -> PractitionerRead:
        # Practitioner has no name of its own — it's a role attached to an
        # existing User — so every read needs a join back to that user for
        # display purposes (there's no practitioner list UI that would want
        # just a bare user_id).
        user = await self.users.get_by_id(practitioner.user_id)
        if user is None:
            raise NotFoundError("User", practitioner.user_id)
        return PractitionerRead(
            id=practitioner.id,
            organization_id=practitioner.organization_id,
            user_id=practitioner.user_id,
            specialty=practitioner.specialty,
            is_active=practitioner.is_active,
            full_name=user.full_name,
            email=user.email,
        )

    async def create(
        self, organization_id: uuid.UUID, data: PractitionerCreate
    ) -> PractitionerRead:
        user = await self.users.get_by_id(data.user_id)
        if user is None or user.organization_id != organization_id:
            raise NotFoundError("User", data.user_id)
        if await self.repository.get_by_user_id(organization_id, data.user_id) is not None:
            raise ConflictError("This user already has a practitioner profile")

        practitioner = Practitioner(organization_id=organization_id, **data.model_dump())
        practitioner = await self.repository.create(practitioner)
        return await self._to_read(practitioner)

    async def list_active(
        self, organization_id: uuid.UUID, include_inactive: bool = False
    ) -> list[PractitionerRead]:
        practitioners = await self.repository.list_active(organization_id, include_inactive)
        return [await self._to_read(p) for p in practitioners]

    async def update(
        self, organization_id: uuid.UUID, practitioner_id: uuid.UUID, data: PractitionerUpdate
    ) -> PractitionerRead:
        practitioner = await self.repository.get(organization_id, practitioner_id)
        if practitioner is None:
            raise NotFoundError("Practitioner", practitioner_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(practitioner, field, value)
        return await self._to_read(practitioner)
