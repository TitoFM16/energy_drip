import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from medical_api.core.database import (
    Base,
    OrganizationScopedMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class TreatmentPlanStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TreatmentDefinition(Base, UUIDPrimaryKeyMixin, TimestampMixin, OrganizationScopedMixin):
    __tablename__ = "treatment_definitions"

    name: Mapped[str] = mapped_column(String(150))
    description: Mapped[str | None]
    default_session_count: Mapped[int] = mapped_column(default=1)
    is_active: Mapped[bool] = mapped_column(default=True)


class TreatmentPlan(Base, UUIDPrimaryKeyMixin, TimestampMixin, OrganizationScopedMixin):
    __tablename__ = "treatment_plans"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), index=True
    )
    treatment_definition_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("treatment_definitions.id")
    )
    status: Mapped[TreatmentPlanStatus] = mapped_column(default=TreatmentPlanStatus.ACTIVE)
    planned_session_count: Mapped[int]
    notes: Mapped[str | None]


class TreatmentSession(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "treatment_sessions"

    treatment_plan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("treatment_plans.id", ondelete="CASCADE"), index=True
    )
    appointment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("appointments.id", ondelete="SET NULL")
    )
    practitioner_id: Mapped[uuid.UUID]
    session_number: Mapped[int]
    performed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    clinical_evolution: Mapped[str | None]


class TreatmentFormula(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "treatment_formulas"

    treatment_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("treatment_sessions.id", ondelete="CASCADE"), index=True
    )
    ingredients: Mapped[str]
    concentration_notes: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Followup(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "followups"

    treatment_plan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("treatment_plans.id", ondelete="CASCADE")
    )
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None]


class Attachment(Base, UUIDPrimaryKeyMixin, OrganizationScopedMixin):
    __tablename__ = "attachments"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), index=True
    )
    treatment_session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("treatment_sessions.id")
    )
    storage_key: Mapped[str]
    content_type: Mapped[str] = mapped_column(String(100))
    uploaded_by_user_id: Mapped[uuid.UUID]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
