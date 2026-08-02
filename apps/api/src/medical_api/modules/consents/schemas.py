import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from medical_api.modules.consents.models import (
    ConsentRequestStatus,
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


class ConsentSubmissionRead(BaseModel):
    id: uuid.UUID
    submitted_at: datetime
    timezone: str
    eligibility_result: EligibilityResult
    has_signature: bool
    answers: list[ConsentAnswerRead]


class ConsentRequestDetail(ConsentRequestRead):
    submission: ConsentSubmissionRead | None = None
