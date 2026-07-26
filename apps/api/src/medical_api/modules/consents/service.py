import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from medical_api.integrations.object_storage.client import upload_bytes
from medical_api.modules.consents.models import (
    ConsentAnswer,
    ConsentEvent,
    ConsentRequest,
    ConsentRequestStatus,
    ConsentSignature,
    ConsentSubmission,
)
from medical_api.modules.consents.repository import ConsentRepository
from medical_api.modules.consents.schemas import (
    ConsentFormRead,
    ConsentQuestionPublic,
    ConsentSubmissionCreate,
)
from medical_api.modules.notifications.service import enqueue_event
from medical_api.shared.domain.eligibility import evaluate_rules

CONSENT_LINK_TTL = timedelta(hours=48)


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


def generate_consent_token() -> tuple[str, str]:
    raw_token = secrets.token_urlsafe(32)
    return raw_token, hash_token(raw_token)


class ConsentService:
    def __init__(self, repository: ConsentRepository, session: AsyncSession):
        self.repository = repository
        self.session = session

    async def create_request(
        self,
        organization_id: uuid.UUID,
        patient_id: uuid.UUID,
        appointment_id: uuid.UUID | None,
        template_version_id: uuid.UUID,
    ) -> tuple[ConsentRequest, str]:
        raw_token, token_hash = generate_consent_token()
        request = ConsentRequest(
            organization_id=organization_id,
            patient_id=patient_id,
            appointment_id=appointment_id,
            template_version_id=template_version_id,
            token_hash=token_hash,
            expires_at=datetime.now(UTC) + CONSENT_LINK_TTL,
        )
        self.session.add(request)
        await self.session.flush()
        return request, raw_token

    async def get_form(self, raw_token: str) -> ConsentFormRead:
        request = await self._resolve_active_request(raw_token)
        version = await self.repository.get_template_version(request.template_version_id)
        questions = await self.repository.list_questions(request.template_version_id)
        question_payloads = []
        for question in questions:
            options = await self.repository.list_options(question.id)
            question_payloads.append(
                ConsentQuestionPublic(
                    id=question.id,
                    field_key=question.field_key,
                    prompt=question.prompt,
                    question_type=question.question_type,
                    display_order=question.display_order,
                    is_required=question.is_required,
                    options=[{"value": o.value, "label": o.label} for o in options],
                )
            )
        return ConsentFormRead(
            consent_request_id=request.id,
            template_version_id=request.template_version_id,
            body_markdown=version.body_markdown if version else "",
            questions=question_payloads,
            expires_at=request.expires_at,
        )

    async def _resolve_active_request(self, raw_token: str) -> ConsentRequest:
        request = await self.repository.get_request_by_token_hash(hash_token(raw_token))
        if request is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Consent link not found")
        if request.status != ConsentRequestStatus.PENDING:
            raise HTTPException(status.HTTP_410_GONE, "Consent link already used or invalidated")
        if request.expires_at < datetime.now(UTC):
            request.status = ConsentRequestStatus.EXPIRED
            raise HTTPException(status.HTTP_410_GONE, "Consent link has expired")
        return request

    async def submit(
        self,
        raw_token: str,
        data: ConsentSubmissionCreate,
        ip_address: str,
        user_agent: str,
    ) -> ConsentSubmission:
        request = await self._resolve_active_request(raw_token)
        rules = await self.repository.list_rules(request.template_version_id)
        answers_by_field = {answer.field_key: answer.value for answer in data.answers}
        eligibility_result = evaluate_rules(
            [{"rule": rule.rule, "result": rule.result} for rule in rules], answers_by_field
        )

        submission = ConsentSubmission(
            consent_request_id=request.id,
            timezone=data.timezone,
            ip_address=ip_address,
            user_agent=user_agent,
            eligibility_result=eligibility_result,
        )
        self.session.add(submission)
        await self.session.flush()

        for answer in data.answers:
            self.session.add(
                ConsentAnswer(
                    submission_id=submission.id,
                    question_id=answer.question_id,
                    field_key=answer.field_key,
                    value={"value": answer.value},
                )
            )

        signature_key = (
            f"organizations/{request.organization_id}/patients/{request.patient_id}/"
            f"signatures/{uuid.uuid4()}.svg"
        )
        upload_bytes(signature_key, data.signature_svg.encode(), "image/svg+xml")
        self.session.add(
            ConsentSignature(submission_id=submission.id, signature_svg_path=signature_key)
        )

        request.status = ConsentRequestStatus.COMPLETED
        self.session.add(
            ConsentEvent(
                consent_request_id=request.id, event_type="consent.submitted", event_metadata={}
            )
        )

        # Same transaction as the submission: the worker picks this up to
        # generate the immutable PDF (see docs/architecture for the flow).
        await enqueue_event(
            self.session,
            organization_id=request.organization_id,
            event_type="consent.submitted",
            payload={"consent_request_id": str(request.id), "submission_id": str(submission.id)},
        )
        return submission
