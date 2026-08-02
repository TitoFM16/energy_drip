import uuid
from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import Date, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from medical_api.core.database import Base, OrganizationScopedMixin, UUIDPrimaryKeyMixin


class BookingRequestStatus(StrEnum):
    PENDING = "pending"
    CONTACTED = "contacted"
    SCHEDULED = "scheduled"
    DECLINED = "declined"


class BookingRequest(Base, UUIDPrimaryKeyMixin, OrganizationScopedMixin):
    """A patient-submitted request from the public /reservar form — not an
    Appointment. Staff review it and create the real Patient/Appointment
    through the existing internal flows once they've confirmed a slot with
    the person by phone; this table only ever holds what an anonymous
    caller volunteered, never anything derived from the real schedule.
    """

    __tablename__ = "booking_requests"

    treatment_definition_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("treatment_definitions.id")
    )
    first_name: Mapped[str] = mapped_column(String(150))
    last_name: Mapped[str] = mapped_column(String(150))
    phone_number: Mapped[str] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(255))
    preferred_date: Mapped[date | None] = mapped_column(Date)
    message: Mapped[str | None]
    status: Mapped[BookingRequestStatus] = mapped_column(default=BookingRequestStatus.PENDING)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
