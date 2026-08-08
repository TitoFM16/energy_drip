import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from medical_api.core.exceptions import ConflictError, NotFoundError
from medical_api.integrations.object_storage.client import upload_bytes
from medical_api.modules.audit.service import AuditService
from medical_api.modules.consents.models import (
    ConsentAnswer,
    ConsentEvent,
    ConsentQuestion,
    ConsentQuestionOption,
    ConsentRequest,
    ConsentRequestStatus,
    ConsentSignature,
    ConsentSubmission,
    ConsentTemplate,
    ConsentTemplateVersion,
)
from medical_api.modules.consents.repository import ConsentRepository, ConsentTemplateRepository
from medical_api.modules.consents.schemas import (
    ConsentAnswerRead,
    ConsentFormRead,
    ConsentQuestionPublic,
    ConsentRequestDetail,
    ConsentSubmissionCreate,
    ConsentSubmissionRead,
    ConsentTemplateCreate,
    ConsentTemplateRead,
)
from medical_api.modules.notifications.service import enqueue_event
from medical_api.shared.domain.eligibility import evaluate_rules
from medical_api.shared.utilities.tokens import generate_opaque_token, hash_token

CONSENT_LINK_TTL = timedelta(hours=48)


class ConsentTemplateService:
    def __init__(self, repository: ConsentTemplateRepository):
        self.repository = repository

    async def create(
        self, organization_id: uuid.UUID, data: ConsentTemplateCreate
    ) -> ConsentTemplateRead:
        template = ConsentTemplate(organization_id=organization_id, name=data.name)
        await self.repository.create_template(template)

        version = ConsentTemplateVersion(
            template_id=template.id, version_number=1, body_markdown=data.body_markdown
        )
        await self.repository.create_version(version)

        for question_data in data.questions:
            question = ConsentQuestion(
                template_version_id=version.id,
                field_key=question_data.field_key,
                prompt=question_data.prompt,
                question_type=question_data.question_type,
                display_order=question_data.display_order,
                is_required=question_data.is_required,
            )
            await self.repository.create_question(question)
            for option_data in question_data.options:
                await self.repository.create_option(
                    ConsentQuestionOption(
                        question_id=question.id, value=option_data.value, label=option_data.label
                    )
                )

        return await self._to_read(template)

    async def _to_read(self, template: ConsentTemplate) -> ConsentTemplateRead:
        latest_version = await self.repository.get_latest_version(template.id)
        return ConsentTemplateRead(
            id=template.id,
            name=template.name,
            is_active=template.is_active,
            latest_version=latest_version,
        )

    async def list_all(self, organization_id: uuid.UUID) -> list[ConsentTemplateRead]:
        templates = await self.repository.list_templates(organization_id)
        return [await self._to_read(t) for t in templates]

    async def publish_version(
        self, organization_id: uuid.UUID, template_id: uuid.UUID, version_id: uuid.UUID
    ) -> ConsentTemplateVersion:
        template = await self.repository.get_template(organization_id, template_id)
        if template is None:
            raise NotFoundError("ConsentTemplate", template_id)
        version = await self.repository.get_version(version_id)
        if version is None or version.template_id != template_id:
            raise NotFoundError("ConsentTemplateVersion", version_id)
        if version.published_at is not None:
            raise ConflictError("This version is already published")
        version.published_at = datetime.now(UTC)
        return version


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
        raw_token, token_hash = generate_opaque_token()
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
        # No actor_user_id — the patient authenticates via the single-use
        # token, not a staff session.
        await AuditService(self.session).record(
            organization_id=request.organization_id,
            actor_user_id=None,
            action="consent_request.submitted",
            resource_type="consent_request",
            resource_id=str(request.id),
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"eligibility_result": submission.eligibility_result},
        )
        return submission

    async def list_requests(
        self,
        organization_id: uuid.UUID,
        patient_id: uuid.UUID | None,
        *,
        status: ConsentRequestStatus | None = None,
        needs_review: bool = False,
    ) -> list[ConsentRequest]:
        return await self.repository.list_requests(
            organization_id,
            patient_id,
            status=status,
            needs_review=needs_review,
        )

    async def get_request_detail(
        self, organization_id: uuid.UUID, request_id: uuid.UUID
    ) -> ConsentRequestDetail:
        request = await self.repository.get_request(request_id)
        if request is None or request.organization_id != organization_id:
            raise NotFoundError("ConsentRequest", request_id)

        submission_read: ConsentSubmissionRead | None = None
        submission = await self.repository.get_submission_by_request(request.id)
        if submission is not None:
            answers = await self.repository.list_answers(submission.id)
            signature = await self.repository.get_signature(submission.id)
            submission_read = ConsentSubmissionRead(
                id=submission.id,
                submitted_at=submission.submitted_at,
                timezone=submission.timezone,
                eligibility_result=submission.eligibility_result,
                has_signature=signature is not None,
                answers=[
                    ConsentAnswerRead(
                        question_id=a.question_id, field_key=a.field_key, value=a.value.get("value")
                    )
                    for a in answers
                ],
            )

        return ConsentRequestDetail(
            id=request.id,
            patient_id=request.patient_id,
            appointment_id=request.appointment_id,
            template_version_id=request.template_version_id,
            status=request.status,
            expires_at=request.expires_at,
            created_at=request.created_at,
            submission=submission_read,
        )
