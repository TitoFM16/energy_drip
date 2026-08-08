"""Validates patient-submitted consent answers against a template version's
real questions before they're persisted or fed into eligibility evaluation.

The submission endpoint is unauthenticated (single-use token only), so this
is the only line of defense against a client sending answers for questions
that don't exist, that don't belong to this template version, or whose
values don't match the question's declared type — any of which would
otherwise flow straight into `evaluate_rules` and the generated PDF.
"""

import uuid
from typing import Any

from fastapi import HTTPException, status

from medical_api.modules.consents.models import ConsentQuestion, ConsentQuestionOption, QuestionType
from medical_api.modules.consents.schemas import ConsentAnswerInput

MAX_TEXT_ANSWER_LENGTH = 5000


def _invalid(reason: str, question_id: uuid.UUID | None = None) -> HTTPException:
    detail: dict[str, Any] = {"reason": reason}
    if question_id is not None:
        detail["question_id"] = str(question_id)
    return HTTPException(status.HTTP_400_BAD_REQUEST, detail=detail)


def _validate_value(question: ConsentQuestion, valid_option_values: set[str], value: Any) -> Any:
    qtype = question.question_type
    required = question.is_required

    if qtype == QuestionType.BOOLEAN:
        if not isinstance(value, bool):
            raise _invalid("invalid_answer_value", question.id)
        return value

    if qtype == QuestionType.SINGLE_CHOICE:
        if value is None and not required:
            return None
        if not isinstance(value, str) or value not in valid_option_values:
            raise _invalid("invalid_answer_value", question.id)
        return value

    if qtype == QuestionType.MULTIPLE_CHOICE:
        if (
            not isinstance(value, list)
            or not all(isinstance(item, str) for item in value)
            or len(set(value)) != len(value)
            or not set(value).issubset(valid_option_values)
        ):
            raise _invalid("invalid_answer_value", question.id)
        if required and not value:
            raise _invalid("missing_required_answer", question.id)
        return value

    if qtype == QuestionType.TEXT:
        if value is None and not required:
            return None
        if not isinstance(value, str) or len(value) > MAX_TEXT_ANSWER_LENGTH:
            raise _invalid("invalid_answer_value", question.id)
        if required and not value.strip():
            raise _invalid("missing_required_answer", question.id)
        return value

    if qtype == QuestionType.NUMBER:
        if value is None and not required:
            return None
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise _invalid("invalid_answer_value", question.id)
        return value

    raise _invalid("invalid_answer_value", question.id)


def validate_submission_answers(
    questions: list[ConsentQuestion],
    options: list[ConsentQuestionOption],
    answers: list[ConsentAnswerInput],
) -> dict[uuid.UUID, Any]:
    """Returns a {question_id: normalized_value} map covering every answered
    question. Raises HTTPException(400) on the first unknown question,
    duplicate answer, field_key mismatch, missing required answer, or
    value that doesn't match its question's declared type/options.
    """
    if len(answers) > len(questions):
        raise _invalid("too_many_answers")

    questions_by_id = {question.id: question for question in questions}
    options_by_question: dict[uuid.UUID, set[str]] = {}
    for option in options:
        options_by_question.setdefault(option.question_id, set()).add(option.value)

    normalized: dict[uuid.UUID, Any] = {}
    for answer in answers:
        if answer.question_id in normalized:
            raise _invalid("duplicate_answer", answer.question_id)

        question = questions_by_id.get(answer.question_id)
        if question is None:
            raise _invalid("unknown_question", answer.question_id)
        if question.field_key != answer.field_key:
            raise _invalid("field_key_mismatch", answer.question_id)

        normalized[question.id] = _validate_value(
            question, options_by_question.get(question.id, set()), answer.value
        )

    for question in questions:
        if question.is_required and question.id not in normalized:
            raise _invalid("missing_required_answer", question.id)

    return normalized
