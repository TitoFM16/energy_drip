import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from medical_api.core.database import (
    Base,
    OrganizationScopedMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class EligibilityResult(StrEnum):
    ELIGIBLE = "eligible"
    REQUIRES_MANUAL_REVIEW = "requires_manual_review"
    NOT_ELIGIBLE = "not_eligible"


class ConsentReviewDecision(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"


class ConsentRequestStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    EXPIRED = "expired"
    INVALIDATED = "invalidated"


class QuestionType(StrEnum):
    BOOLEAN = "boolean"
    SINGLE_CHOICE = "single_choice"
    MULTIPLE_CHOICE = "multiple_choice"
    TEXT = "text"
    NUMBER = "number"


class ConsentTemplate(Base, UUIDPrimaryKeyMixin, TimestampMixin, OrganizationScopedMixin):
    __tablename__ = "consent_templates"

    name: Mapped[str] = mapped_column(String(150))
    is_active: Mapped[bool] = mapped_column(default=True)


class ConsentTemplateVersion(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "consent_template_versions"

    template_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("consent_templates.id", ondelete="CASCADE")
    )
    version_number: Mapped[int]
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    body_markdown: Mapped[str]


class ConsentQuestion(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "consent_questions"

    template_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("consent_template_versions.id", ondelete="CASCADE"), index=True
    )
    field_key: Mapped[str] = mapped_column(String(100))
    prompt: Mapped[str]
    question_type: Mapped[QuestionType]
    display_order: Mapped[int] = mapped_column(default=0)
    is_required: Mapped[bool] = mapped_column(default=True)


class ConsentQuestionOption(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "consent_question_options"

    question_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("consent_questions.id", ondelete="CASCADE")
    )
    value: Mapped[str] = mapped_column(String(100))
    label: Mapped[str]


class ConsentRule(Base, UUIDPrimaryKeyMixin):
    """Versioned eligibility rule evaluated server-side against submitted
    answers; see `medical_api.shared.domain.eligibility` for the evaluator.
    """

    __tablename__ = "consent_rules"

    template_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("consent_template_versions.id", ondelete="CASCADE")
    )
    rule: Mapped[dict[str, Any]] = mapped_column(JSON)
    result: Mapped[EligibilityResult]
    priority: Mapped[int] = mapped_column(default=0)


class ConsentRequest(Base, UUIDPrimaryKeyMixin, TimestampMixin, OrganizationScopedMixin):
    """A short-lived, single-use consent link. Only the SHA-256 hash of the
    opaque token is stored; the raw token is never persisted.
    """

    __tablename__ = "consent_requests"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), index=True
    )
    appointment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("appointments.id", ondelete="SET NULL")
    )
    template_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("consent_template_versions.id")
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    status: Mapped[ConsentRequestStatus] = mapped_column(default=ConsentRequestStatus.PENDING)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ConsentSubmission(Base, UUIDPrimaryKeyMixin):
    """Patient-supplied content is immutable once created: answers and the
    eligibility result are never updated in place. A correction requires a
    new `ConsentRequest` and submission. The nullable review fields are the
    sole exception and may transition exactly once from unset to finalized.
    """

    __tablename__ = "consent_submissions"
    __table_args__ = (
        CheckConstraint(
            "(review_decision IS NULL AND review_rationale IS NULL "
            "AND reviewed_by_user_id IS NULL AND reviewed_at IS NULL) OR "
            "(review_decision IS NOT NULL AND review_rationale IS NOT NULL "
            "AND reviewed_by_user_id IS NOT NULL AND reviewed_at IS NOT NULL)",
            name="ck_consent_submissions_review_metadata_complete",
        ),
    )

    consent_request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("consent_requests.id", ondelete="CASCADE"), unique=True
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    timezone: Mapped[str]
    ip_address: Mapped[str]
    user_agent: Mapped[str]
    eligibility_result: Mapped[EligibilityResult]
    review_decision: Mapped[ConsentReviewDecision | None]
    review_rationale: Mapped[str | None] = mapped_column(String(2000))
    reviewed_by_user_id: Mapped[uuid.UUID | None]
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ConsentAnswer(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "consent_answers"

    submission_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("consent_submissions.id", ondelete="CASCADE"), index=True
    )
    question_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("consent_questions.id"))
    field_key: Mapped[str] = mapped_column(String(100))
    value: Mapped[dict[str, Any]] = mapped_column(JSON)


class ConsentSignature(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "consent_signatures"

    submission_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("consent_submissions.id", ondelete="CASCADE"), unique=True
    )
    signature_svg_path: Mapped[str]
    signed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ConsentDocument(Base, UUIDPrimaryKeyMixin):
    """Points at an immutable, versioned object in storage. Regeneration
    creates a new row/version rather than overwriting the storage object —
    a document row is never deleted or updated in place except to flip
    is_current (when a later version supersedes it) or to invalidate it.
    """

    __tablename__ = "consent_documents"

    submission_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("consent_submissions.id", ondelete="CASCADE"), index=True
    )
    storage_key: Mapped[str]
    storage_version_id: Mapped[str | None]
    sha256_hash: Mapped[str] = mapped_column(String(64))
    document_version: Mapped[int] = mapped_column(default=1)
    is_current: Mapped[bool] = mapped_column(default=True)
    # Why this version exists — None for the original, automatic
    # generation; set to the staff-supplied reason for any later version
    # created via regeneration.
    regenerated_reason: Mapped[str | None]
    invalidated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    invalidated_reason: Mapped[str | None]
    invalidated_by_user_id: Mapped[uuid.UUID | None]
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ConsentEvent(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "consent_events"

    consent_request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("consent_requests.id", ondelete="CASCADE"), index=True
    )
    event_type: Mapped[str] = mapped_column(String(100))
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    event_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
