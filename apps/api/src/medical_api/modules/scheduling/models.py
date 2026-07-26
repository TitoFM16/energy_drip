import uuid
from datetime import datetime, time
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from medical_api.core.database import (
    Base,
    OrganizationScopedMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class AppointmentStatus(StrEnum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    CONSENT_PENDING = "consent_pending"
    CONSENT_COMPLETED = "consent_completed"
    CHECKED_IN = "checked_in"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class Location(Base, UUIDPrimaryKeyMixin, TimestampMixin, OrganizationScopedMixin):
    __tablename__ = "locations"

    name: Mapped[str] = mapped_column(String(150))
    address: Mapped[str | None]
    timezone: Mapped[str] = mapped_column(default="America/Bogota")


class Room(Base, UUIDPrimaryKeyMixin, OrganizationScopedMixin):
    __tablename__ = "rooms"

    location_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("locations.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(100))


class Practitioner(Base, UUIDPrimaryKeyMixin, TimestampMixin, OrganizationScopedMixin):
    __tablename__ = "practitioners"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    specialty: Mapped[str | None] = mapped_column(String(150))
    is_active: Mapped[bool] = mapped_column(default=True)


class AvailabilityRule(Base, UUIDPrimaryKeyMixin, OrganizationScopedMixin):
    __tablename__ = "availability_rules"

    practitioner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("practitioners.id", ondelete="CASCADE")
    )
    weekday: Mapped[int]  # 0 = Monday ... 6 = Sunday
    start_time: Mapped[time]
    end_time: Mapped[time]


class Appointment(Base, UUIDPrimaryKeyMixin, TimestampMixin, OrganizationScopedMixin):
    __tablename__ = "appointments"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="RESTRICT"), index=True
    )
    practitioner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("practitioners.id", ondelete="RESTRICT")
    )
    room_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("rooms.id", ondelete="SET NULL"))
    treatment_definition_id: Mapped[uuid.UUID | None]
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[AppointmentStatus] = mapped_column(default=AppointmentStatus.SCHEDULED)
    notes: Mapped[str | None]


class AppointmentStatusHistory(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "appointment_status_history"

    appointment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("appointments.id", ondelete="CASCADE"), index=True
    )
    from_status: Mapped[AppointmentStatus | None]
    to_status: Mapped[AppointmentStatus]
    changed_by_user_id: Mapped[uuid.UUID | None]
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reason: Mapped[str | None]
