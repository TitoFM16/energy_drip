import uuid
from datetime import date, datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from medical_api.core.database import (
    Base,
    OrganizationScopedMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class Patient(Base, UUIDPrimaryKeyMixin, TimestampMixin, OrganizationScopedMixin):
    __tablename__ = "patients"

    first_name: Mapped[str] = mapped_column(String(150))
    last_name: Mapped[str] = mapped_column(String(150))
    document_id: Mapped[str | None] = mapped_column(String(50), index=True)
    date_of_birth: Mapped[date | None]
    phone_number: Mapped[str | None]
    email: Mapped[str | None]
    is_active: Mapped[bool] = mapped_column(default=True)
    whatsapp_opt_out: Mapped[bool] = mapped_column(default=False)
    whatsapp_opt_out_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Product simplification: recording a phone number through the staff
    # patient workflow is currently the only consent-to-contact touchpoint,
    # so its first occurrence is retained as WhatsApp opt-in evidence. This
    # is not a signed consent and must be revisited during compliance review.
    whatsapp_opt_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PatientContact(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "patient_contacts"

    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"))
    label: Mapped[str] = mapped_column(String(50))
    phone_number: Mapped[str | None]
    email: Mapped[str | None]


class EmergencyContact(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "emergency_contacts"

    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"))
    full_name: Mapped[str]
    relationship: Mapped[str | None]
    phone_number: Mapped[str]
