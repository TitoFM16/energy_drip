import uuid
from datetime import date

from sqlalchemy import ForeignKey, String
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
