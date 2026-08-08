import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from medical_api.modules.consents.models import (
    ConsentRequestStatus,
    ConsentReviewDecision,
    EligibilityResult,
    QuestionType,
)


class ConsentQuestionOptionInput(BaseModel):
    value: str
    label: str


class ConsentQuestionInput(BaseModel):
    field_key: str
    prompt: str
    question_type: QuestionType
    display_order: int = 0
    is_required: bool = True
    options: list[ConsentQuestionOptionInput] = []


class ConsentTemplateCreate(BaseModel):
    """Creates a template and its first draft version together. Staff
    author the consent text and questions in one pass; eligibility rules
    aren't exposed in the authoring form yet (see the module's remaining
    gaps) — with none configured, every submission safely falls through to
    `requires_manual_review` rather than silently auto-approving.
    """

    name: str
    body_markdown: str
    questions: list[ConsentQuestionInput] = []


class ConsentTemplateVersionRead(BaseModel):
    id: uuid.UUID
    template_id: uuid.UUID
    version_number: int
    published_at: datetime | None
    body_markdown: str

    model_config = {"from_attributes": True}


class ConsentTemplateRead(BaseModel):
    id: uuid.UUID
    name: str
    is_active: bool
    latest_version: ConsentTemplateVersionRead | None = None


class ConsentQuestionPublic(BaseModel):
    id: uuid.UUID
    field_key: str
    prompt: str
    question_type: QuestionType
    display_order: int
    is_required: bool
    options: list[dict[str, str]] = []


class ConsentTemplateVersionDetail(ConsentTemplateVersionRead):
    """Staff-side view of a version's full content — unlike the public
    consent-form endpoint, this doesn't require an active pending request,
    so it also works for reviewing an already-completed submission's
    original questions.
    """

    questions: list[ConsentQuestionPublic]


class ConsentFormRead(BaseModel):
    consent_request_id: uuid.UUID
    template_version_id: uuid.UUID
    body_markdown: str
    questions: list[ConsentQuestionPublic]
    expires_at: datetime


class ConsentAnswerInput(BaseModel):
    question_id: uuid.UUID
    field_key: str
    value: Any


class ConsentSubmissionCreate(BaseModel):
    answers: list[ConsentAnswerInput]
    signature_svg: str
    timezone: str


class ConsentSubmissionResult(BaseModel):
    submission_id: uuid.UUID
    eligibility_result: EligibilityResult


class ConsentSubmissionReviewCreate(BaseModel):
    decision: ConsentReviewDecision
    rationale: str = Field(min_length=1, max_length=2000)

    @field_validator("rationale")
    @classmethod
    def strip_rationale(cls, rationale: str) -> str:
        rationale = rationale.strip()
        if not rationale:
            raise ValueError("Rationale must not be blank")
        return rationale


class ConsentSubmissionReviewRead(BaseModel):
    decision: ConsentReviewDecision
    rationale: str
    reviewed_by_user_id: uuid.UUID
    reviewed_by_name: str
    reviewed_at: datetime


class ConsentRequestInvalidate(BaseModel):
    reason: str


class ConsentRequestRead(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    appointment_id: uuid.UUID | None
    template_version_id: uuid.UUID
    status: ConsentRequestStatus
    expires_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class ConsentAnswerRead(BaseModel):
    question_id: uuid.UUID
    field_key: str
    value: Any


class DocumentRead(BaseModel):
    id: uuid.UUID
    submission_id: uuid.UUID
    sha256_hash: str
    document_version: int
    is_current: bool
    regenerated_reason: str | None
    invalidated_at: datetime | None
    invalidated_reason: str | None
    generated_at: datetime

    model_config = {"from_attributes": True}


class ConsentSubmissionRead(BaseModel):
    id: uuid.UUID
    submitted_at: datetime
    timezone: str
    eligibility_result: EligibilityResult
    review_decision: ConsentReviewDecision | None
    review_rationale: str | None
    reviewed_by_user_id: uuid.UUID | None
    reviewed_by_name: str | None
    reviewed_at: datetime | None
    has_signature: bool
    answers: list[ConsentAnswerRead]
    # Empty until the worker finishes generating the PDF (async, off the
    # consent.submitted event) — the review workspace polls/refetches
    # rather than the API making the client wait on it synchronously.
    documents: list[DocumentRead] = []


class ConsentRequestDetail(ConsentRequestRead):
    submission: ConsentSubmissionRead | None = None


class DocumentDownloadRead(BaseModel):
    url: str
    expires_in: int


class DocumentVerifyResult(BaseModel):
    sha256_hash: str
    recomputed_hash: str
    matches: bool
    verified_at: datetime


class DocumentInvalidate(BaseModel):
    reason: str


class DocumentRegenerate(BaseModel):
    reason: str
