import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from medical_api.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PatientMedicalHistory(Base, UUIDPrimaryKeyMixin):
    """Append-only, like ClinicalNote: a finalized entry is never edited in
    place. Corrections are added as new entries referencing
    `amends_entry_id`.
    """

    __tablename__ = "patient_medical_histories"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), index=True
    )
    author_user_id: Mapped[uuid.UUID]
    summary: Mapped[str]
    is_finalized: Mapped[bool] = mapped_column(default=False)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    amends_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("patient_medical_histories.id")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PatientAllergy(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "patient_allergies"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), index=True
    )
    substance: Mapped[str] = mapped_column(String(150))
    severity: Mapped[str | None] = mapped_column(String(50))
    notes: Mapped[str | None]
    is_active: Mapped[bool] = mapped_column(default=True)


class PatientCondition(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "patient_conditions"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(150))
    diagnosed_on: Mapped[datetime | None]
    notes: Mapped[str | None]
    is_active: Mapped[bool] = mapped_column(default=True)


class PatientMedication(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "patient_medications"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(150))
    dosage: Mapped[str | None]
    is_current: Mapped[bool] = mapped_column(default=True)


class ClinicalNote(Base, UUIDPrimaryKeyMixin):
    """Append-only: a finalized note is never edited in place. Corrections are
    added as new notes referencing `amends_note_id`.
    """

    __tablename__ = "clinical_notes"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), index=True
    )
    author_user_id: Mapped[uuid.UUID]
    appointment_id: Mapped[uuid.UUID | None]
    content: Mapped[str]
    is_finalized: Mapped[bool] = mapped_column(default=False)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    amends_note_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("clinical_notes.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
