import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from medical_api.modules.consents.models import EligibilityResult, QuestionType


class ConsentQuestionPublic(BaseModel):
    id: uuid.UUID
    field_key: str
    prompt: str
    question_type: QuestionType
    display_order: int
    is_required: bool
    options: list[dict[str, str]] = []


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
