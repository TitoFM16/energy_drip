import uuid
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from medical_api.core.config import get_settings
from medical_api.core.exceptions import ConflictError, NotFoundError
from medical_api.core.security import hash_password
from medical_api.modules.identity.models import User
from medical_api.modules.identity.repository import UserRepository
from medical_api.modules.patients.repository import PatientRepository
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
    RoomRepository,
)
from medical_api.modules.scheduling.schemas import (
    AppointmentCreate,
    AppointmentRead,
    AppointmentStatusHistoryRead,
    AvailabilityRuleCreate,
    AvailableSlot,
    PractitionerCreate,
    PractitionerRead,
    PractitionerUpdate,
)
from medical_api.modules.treatments.repository import TreatmentDefinitionRepository

MAX_AVAILABILITY_WINDOW_DAYS = 31


class AppointmentService:
    def __init__(
        self,
        repository: AppointmentRepository,
        session: AsyncSession,
        *,
        patients: PatientRepository | None = None,
        practitioners: PractitionerRepository | None = None,
        availability: AvailabilityRepository | None = None,
        rooms: RoomRepository | None = None,
        users: UserRepository | None = None,
        timezone: str | None = None,
    ):
        self.repository = repository
        self.session = session
        self.patients = patients or PatientRepository(session)
        self.practitioners = practitioners or PractitionerRepository(session)
        self.availability = availability or AvailabilityRepository(session)
        self.rooms = rooms or RoomRepository(session)
        self.users = users or UserRepository(session)
        self.timezone = ZoneInfo(timezone or get_settings().clinic_timezone)
        self.treatments = TreatmentDefinitionRepository(session)

    async def schedule(
        self,
        organization_id: uuid.UUID,
        data: AppointmentCreate,
        *,
        actor_user_id: uuid.UUID | None = None,
    ) -> Appointment:
        await self.repository.lock_resources(data.practitioner_id, data.room_id)
        self._check_future_range(data.starts_at, data.ends_at)
        if await self.patients.get(organization_id, data.patient_id) is None:
            raise NotFoundError("Patient", data.patient_id)
        practitioner = await self.practitioners.get(organization_id, data.practitioner_id)
        if practitioner is None or not practitioner.is_active:
            raise NotFoundError("Practitioner", data.practitioner_id)
        await self._check_service(
            organization_id, data.treatment_definition_id, data.starts_at, data.ends_at
        )
        if data.room_id is not None and await self.rooms.get(organization_id, data.room_id) is None:
            raise NotFoundError("Room", data.room_id)

        await self._check_within_availability(
            organization_id, data.practitioner_id, data.starts_at, data.ends_at
        )

        if await self.repository.has_conflict(data.practitioner_id, data.starts_at, data.ends_at):
            raise ConflictError("Practitioner already has an appointment in that time range")
        if data.room_id is not None and await self.repository.has_room_conflict(
            data.room_id, data.starts_at, data.ends_at
        ):
            raise ConflictError("Room already has an appointment in that time range")

        appointment = Appointment(organization_id=organization_id, **data.model_dump())
        await self.repository.create(appointment)
        await self.repository.add_status_history(
            AppointmentStatusHistory(
                appointment_id=appointment.id,
                from_status=None,
                to_status=appointment.status,
                changed_by_user_id=actor_user_id,
            )
        )
        return appointment

    async def _check_within_availability(
        self,
        organization_id: uuid.UUID,
        practitioner_id: uuid.UUID,
        starts_at: datetime,
        ends_at: datetime,
    ) -> None:
        rules = await self.availability.list_rules(organization_id, practitioner_id)
        local_start = starts_at.astimezone(self.timezone)
        weekday = local_start.weekday()
        for rule in rules:
            if rule.weekday != weekday:
                continue
            rule_start = datetime.combine(local_start.date(), rule.start_time, tzinfo=self.timezone)
            rule_end = datetime.combine(local_start.date(), rule.end_time, tzinfo=self.timezone)
            duration = (ends_at - starts_at).total_seconds()
            offset = (starts_at - rule_start).total_seconds()
            if rule_start <= starts_at and ends_at <= rule_end and offset % duration == 0:
                return
        raise ConflictError("Appointment time is outside the practitioner's availability")

    async def change_status(
        self,
        organization_id: uuid.UUID,
        appointment_id: uuid.UUID,
        new_status: AppointmentStatus,
        reason: str | None,
        *,
        actor_user_id: uuid.UUID | None = None,
    ) -> Appointment:
        appointment = await self.repository.get(organization_id, appointment_id)
        if appointment is None:
            raise NotFoundError("Appointment", appointment_id)
        await self.repository.lock_resources(appointment.practitioner_id, appointment.room_id)
        await self.session.refresh(appointment)
        previous_status = appointment.status
        if previous_status == new_status:
            return appointment
        terminal = {
            AppointmentStatus.CANCELLED,
            AppointmentStatus.COMPLETED,
            AppointmentStatus.NO_SHOW,
        }
        if previous_status in terminal:
            raise ConflictError(
                "A finished or cancelled appointment cannot change status; create a new booking"
            )
        appointment.status = new_status
        await self.repository.add_status_history(
            AppointmentStatusHistory(
                appointment_id=appointment.id,
                from_status=previous_status,
                to_status=new_status,
                changed_by_user_id=actor_user_id,
                reason=reason,
            )
        )
        return appointment

    async def reschedule(
        self,
        organization_id: uuid.UUID,
        appointment_id: uuid.UUID,
        starts_at: datetime,
        ends_at: datetime,
    ) -> Appointment:
        appointment = await self.repository.get(organization_id, appointment_id)
        if appointment is None:
            raise NotFoundError("Appointment", appointment_id)
        await self.repository.lock_resources(appointment.practitioner_id, appointment.room_id)
        await self.session.refresh(appointment)
        self._check_future_range(starts_at, ends_at)
        practitioner = await self.practitioners.get(organization_id, appointment.practitioner_id)
        if practitioner is None or not practitioner.is_active:
            raise NotFoundError("Practitioner", appointment.practitioner_id)
        if ends_at - starts_at != appointment.ends_at - appointment.starts_at:
            raise ConflictError("Rescheduling must preserve the booked appointment duration")
        if appointment.treatment_definition_id is not None:
            definition = await self.treatments.get(
                organization_id, appointment.treatment_definition_id, for_update=True
            )
            if definition is None or not definition.is_active:
                raise NotFoundError("TreatmentDefinition", appointment.treatment_definition_id)
        if appointment.status in (
            AppointmentStatus.CANCELLED,
            AppointmentStatus.COMPLETED,
            AppointmentStatus.NO_SHOW,
        ):
            raise ConflictError(f"Cannot reschedule an appointment that is {appointment.status}")

        await self._check_within_availability(
            organization_id, appointment.practitioner_id, starts_at, ends_at
        )
        if await self.repository.has_conflict(
            appointment.practitioner_id, starts_at, ends_at, exclude_appointment_id=appointment.id
        ):
            raise ConflictError("Practitioner already has an appointment in that time range")
        if appointment.room_id is not None and await self.repository.has_room_conflict(
            appointment.room_id, starts_at, ends_at, exclude_appointment_id=appointment.id
        ):
            raise ConflictError("Room already has an appointment in that time range")

        appointment.starts_at = starts_at
        appointment.ends_at = ends_at
        return appointment

    @staticmethod
    def _check_future_range(starts_at: datetime, ends_at: datetime) -> None:
        if starts_at.tzinfo is None or ends_at.tzinfo is None:
            raise ConflictError("Appointment times must include a timezone")
        if starts_at < datetime.now(UTC) or ends_at <= starts_at:
            raise ConflictError("Choose a future appointment time with a positive duration")

    async def _check_service(self, organization_id, definition_id, starts_at, ends_at) -> None:
        if definition_id is None:
            return
        definition = await self.treatments.get(organization_id, definition_id, for_update=True)
        if definition is None or not definition.is_active:
            raise NotFoundError("TreatmentDefinition", definition_id)
        if ends_at - starts_at != timedelta(minutes=definition.duration_minutes):
            raise ConflictError("Appointment duration must match the selected service")

    async def to_read(self, appointment: Appointment) -> AppointmentRead:
        patient = await self.patients.get(appointment.organization_id, appointment.patient_id)
        practitioner = await self.practitioners.get(
            appointment.organization_id, appointment.practitioner_id
        )
        worker = await self.users.get_by_id(practitioner.user_id) if practitioner else None
        treatment = (
            await self.treatments.get(
                appointment.organization_id, appointment.treatment_definition_id
            )
            if appointment.treatment_definition_id
            else None
        )
        return AppointmentRead.model_validate(appointment).model_copy(
            update={
                "patient_name": f"{patient.first_name} {patient.last_name}" if patient else None,
                "patient_phone": patient.phone_number if patient else None,
                "practitioner_name": worker.full_name if worker else None,
                "treatment_name": treatment.name if treatment else None,
            }
        )

    async def get_status_history(
        self, organization_id: uuid.UUID, appointment_id: uuid.UUID
    ) -> list[AppointmentStatusHistoryRead]:
        appointment = await self.repository.get(organization_id, appointment_id)
        if appointment is None:
            raise NotFoundError("Appointment", appointment_id)
        entries = await self.repository.list_status_history(organization_id, appointment_id)

        # One-off lookups, not a join: history entries are few per
        # appointment and often share the same actor, so the extra queries
        # this could in principle avoid aren't worth a join here.
        names_by_user_id: dict[uuid.UUID, str] = {}
        results = []
        for entry in entries:
            full_name = None
            if entry.changed_by_user_id is not None:
                if entry.changed_by_user_id not in names_by_user_id:
                    user = await self.users.get_by_id(entry.changed_by_user_id)
                    if user is not None:
                        names_by_user_id[entry.changed_by_user_id] = user.full_name
                full_name = names_by_user_id.get(entry.changed_by_user_id)
            results.append(
                AppointmentStatusHistoryRead(
                    id=entry.id,
                    from_status=entry.from_status,
                    to_status=entry.to_status,
                    changed_by_user_id=entry.changed_by_user_id,
                    changed_by_full_name=full_name,
                    changed_at=entry.changed_at,
                    reason=entry.reason,
                )
            )
        return results


class AvailabilityService:
    """Weekly rules use clinic local time; appointment timestamps carry UTC offsets."""

    def __init__(
        self,
        repository: AvailabilityRepository,
        appointments: AppointmentRepository,
        *,
        timezone: str | None = None,
    ):
        self.repository = repository
        self.appointments = appointments
        self.timezone = ZoneInfo(timezone or get_settings().clinic_timezone)

    async def create_rule(
        self, organization_id: uuid.UUID, data: AvailabilityRuleCreate
    ) -> AvailabilityRule:
        await self.appointments.lock_resources(data.practitioner_id)
        practitioner = await PractitionerRepository(self.repository.session).get(
            organization_id, data.practitioner_id
        )
        if practitioner is None or not practitioner.is_active:
            raise NotFoundError("Practitioner", data.practitioner_id)
        rules = await self.repository.list_rules(organization_id, data.practitioner_id)
        if any(
            rule.weekday == data.weekday
            and rule.start_time < data.end_time
            and rule.end_time > data.start_time
            for rule in rules
        ):
            raise ConflictError("Availability rules cannot overlap")
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
        await self.appointments.lock_resources(rule.practitioner_id)
        await self.repository.delete_rule(rule)

    async def compute_slots(
        self,
        organization_id: uuid.UUID,
        practitioner_id: uuid.UUID,
        date_from: date,
        date_to: date,
        duration_minutes: int,
    ) -> list[AvailableSlot]:
        if duration_minutes < 5 or duration_minutes > 480:
            raise ConflictError("Duration must be between 5 and 480 minutes")
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

        range_start = datetime.combine(date_from, datetime.min.time(), tzinfo=self.timezone)
        range_end = datetime.combine(
            date_to, datetime.min.time(), tzinfo=self.timezone
        ) + timedelta(days=1)
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
                cursor = datetime.combine(current_day, rule.start_time, tzinfo=self.timezone)
                day_end = datetime.combine(current_day, rule.end_time, tzinfo=self.timezone)
                while cursor + step <= day_end:
                    slot_end = cursor + step
                    if cursor >= now and not _overlaps_any(cursor, slot_end, busy_periods):
                        slots.append(AvailableSlot(starts_at=cursor, ends_at=slot_end))
                    cursor += step
            current_day += timedelta(days=1)
        return sorted(
            {slot.starts_at: slot for slot in slots}.values(), key=lambda slot: slot.starts_at
        )


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
        if data.user_id is not None:
            user = await self.users.get_by_id(data.user_id)
            if user is None or user.organization_id != organization_id:
                raise NotFoundError("User", data.user_id)
            if await self.repository.get_by_user_id(organization_id, data.user_id) is not None:
                raise ConflictError("This user already has a practitioner profile")
        else:
            # A worker on the calendar does not need an account, email or password.
            user = await self.users.create(
                User(
                    organization_id=organization_id,
                    full_name=data.full_name,
                    email=f"worker-{uuid.uuid4()}@staff.invalid",
                    hashed_password=hash_password(str(uuid.uuid4())),
                    is_active=False,
                )
            )
        practitioner = Practitioner(
            organization_id=organization_id, user_id=user.id, specialty=data.specialty
        )
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
        await AppointmentRepository(self.repository.session).lock_resources(practitioner.id)
        await self.repository.session.refresh(practitioner)
        for field, value in data.model_dump(exclude_unset=True).items():
            if field == "full_name":
                user = await self.users.get_by_id(practitioner.user_id)
                user.full_name = value
            else:
                setattr(practitioner, field, value)
        return await self._to_read(practitioner)
