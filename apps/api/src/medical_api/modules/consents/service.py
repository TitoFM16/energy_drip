import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from medical_api.core.exceptions import ConflictError, NotFoundError
from medical_api.integrations.object_storage.client import (
    download_bytes,
    generate_presigned_download_url,
    upload_bytes,
)
from medical_api.modules.audit.service import AuditService
from medical_api.modules.consents.models import (
    ConsentAnswer,
    ConsentDocument,
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
    DocumentVerifyResult,
)
from medical_api.modules.consents.validation import validate_submission_answers
from medical_api.modules.notifications.service import enqueue_event
from medical_api.shared.domain.eligibility import evaluate_rules
from medical_api.shared.utilities.hashing import sha256_hash
from medical_api.shared.utilities.svg_sanitizer import sanitize_signature_svg
from medical_api.shared.utilities.tokens import generate_opaque_token, hash_token

DOCUMENT_DOWNLOAD_URL_TTL_SECONDS = 300

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

    async def _resolve_active_request(
        self, raw_token: str, *, for_update: bool = False
    ) -> ConsentRequest:
        # detail is a small {"reason": ...} dict rather than a free-text
        # string so patient-web can render a distinct message per state
        # ("expired" vs "invalidated" vs "completed") instead of one generic
        # "invalid or expired" message for every failure mode.
        request = await self.repository.get_request_by_token_hash(
            hash_token(raw_token), for_update=for_update
        )
        if request is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"reason": "not_found"})
        if request.status == ConsentRequestStatus.PENDING and request.expires_at < datetime.now(
            UTC
        ):
            request.status = ConsentRequestStatus.EXPIRED
        if request.status == ConsentRequestStatus.COMPLETED:
            raise HTTPException(status.HTTP_410_GONE, detail={"reason": "completed"})
        if request.status == ConsentRequestStatus.INVALIDATED:
            raise HTTPException(status.HTTP_410_GONE, detail={"reason": "invalidated"})
        if request.status == ConsentRequestStatus.EXPIRED:
            raise HTTPException(status.HTTP_410_GONE, detail={"reason": "expired"})
        return request

    async def submit(
        self,
        raw_token: str,
        data: ConsentSubmissionCreate,
        ip_address: str,
        user_agent: str,
    ) -> ConsentSubmission:
        # Row-locked: blocks a concurrent submission of the same token until
        # this transaction commits, instead of racing past the status check
        # above and relying on ConsentSubmission's unique constraint to turn
        # a double-submit into an unhandled IntegrityError.
        request = await self._resolve_active_request(raw_token, for_update=True)

        questions = await self.repository.list_questions(request.template_version_id)
        options = await self.repository.list_options_for_questions([q.id for q in questions])
        # The only validation this unauthenticated endpoint gets: rejects
        # unknown/duplicate/mismatched question IDs, enforces required
        # questions, and checks each value against its question_type.
        normalized_by_question = validate_submission_answers(questions, options, data.answers)

        field_key_by_question = {question.id: question.field_key for question in questions}
        # Eligibility is evaluated from these server-validated values, never
        # from the raw client payload.
        answers_by_field = {
            field_key_by_question[question_id]: value
            for question_id, value in normalized_by_question.items()
        }
        rules = await self.repository.list_rules(request.template_version_id)
        eligibility_result = evaluate_rules(
            [{"rule": rule.rule, "result": rule.result} for rule in rules], answers_by_field
        )

        try:
            sanitized_signature_svg = sanitize_signature_svg(data.signature_svg)
        except ValueError as exc:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail={"reason": "invalid_signature", "message": str(exc)},
            ) from exc

        submission = ConsentSubmission(
            consent_request_id=request.id,
            timezone=data.timezone,
            ip_address=ip_address,
            user_agent=user_agent,
            eligibility_result=eligibility_result,
        )
        self.session.add(submission)
        await self.session.flush()

        for question in questions:
            if question.id not in normalized_by_question:
                continue
            self.session.add(
                ConsentAnswer(
                    submission_id=submission.id,
                    question_id=question.id,
                    field_key=question.field_key,
                    value={"value": normalized_by_question[question.id]},
                )
            )

        signature_key = (
            f"organizations/{request.organization_id}/patients/{request.patient_id}/"
            f"signatures/{uuid.uuid4()}.svg"
        )
        upload_bytes(signature_key, sanitized_signature_svg.encode(), "image/svg+xml")
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

    async def _get_owned_request(
        self, organization_id: uuid.UUID, request_id: uuid.UUID
    ) -> ConsentRequest:
        request = await self.repository.get_request(request_id)
        if request is None or request.organization_id != organization_id:
            raise NotFoundError("ConsentRequest", request_id)
        return request

    async def invalidate_request(
        self, organization_id: uuid.UUID, request_id: uuid.UUID, reason: str
    ) -> ConsentRequest:
        request = await self._get_owned_request(organization_id, request_id)
        if request.status != ConsentRequestStatus.PENDING:
            raise ConflictError(
                f"Only a pending consent request can be invalidated (current status: "
                f"{request.status})"
            )
        request.status = ConsentRequestStatus.INVALIDATED
        self.session.add(
            ConsentEvent(
                consent_request_id=request.id,
                event_type="consent.invalidated",
                event_metadata={"reason": reason},
            )
        )
        return request

    async def resend_request(
        self, organization_id: uuid.UUID, request_id: uuid.UUID
    ) -> tuple[ConsentRequest, str]:
        original = await self._get_owned_request(organization_id, request_id)
        if original.status not in (ConsentRequestStatus.PENDING, ConsentRequestStatus.EXPIRED):
            raise ConflictError(
                f"Only a pending or expired consent request can be resent (current status: "
                f"{original.status})"
            )

        new_request, raw_token = await self.create_request(
            organization_id,
            original.patient_id,
            original.appointment_id,
            original.template_version_id,
        )

        # A still-pending original is superseded so only one link stays
        # live for the same purpose; an already-expired original is left
        # as EXPIRED (it's already a dead link, not "invalidated").
        if original.status == ConsentRequestStatus.PENDING:
            original.status = ConsentRequestStatus.INVALIDATED
        self.session.add(
            ConsentEvent(
                consent_request_id=original.id,
                event_type="consent.resent",
                event_metadata={"new_request_id": str(new_request.id)},
            )
        )
        return new_request, raw_token

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
        request = await self._get_owned_request(organization_id, request_id)

        submission_read: ConsentSubmissionRead | None = None
        submission = await self.repository.get_submission_by_request(request.id)
        if submission is not None:
            answers = await self.repository.list_answers(submission.id)
            signature = await self.repository.get_signature(submission.id)
            documents = await self.repository.list_documents_for_submission(submission.id)
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
                documents=documents,
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


class DocumentService:
    def __init__(self, repository: ConsentRepository, session: AsyncSession):
        self.repository = repository
        self.session = session

    async def _get_owned_document(
        self, organization_id: uuid.UUID, document_id: uuid.UUID
    ) -> ConsentDocument:
        document = await self.repository.get_document_with_org_check(organization_id, document_id)
        if document is None:
            raise NotFoundError("ConsentDocument", document_id)
        return document

    async def get_metadata(
        self, organization_id: uuid.UUID, document_id: uuid.UUID
    ) -> ConsentDocument:
        return await self._get_owned_document(organization_id, document_id)

    async def get_download_url(
        self, organization_id: uuid.UUID, document_id: uuid.UUID
    ) -> tuple[str, int]:
        document = await self._get_owned_document(organization_id, document_id)
        url = generate_presigned_download_url(
            document.storage_key, DOCUMENT_DOWNLOAD_URL_TTL_SECONDS
        )
        return url, DOCUMENT_DOWNLOAD_URL_TTL_SECONDS

    async def verify(
        self, organization_id: uuid.UUID, document_id: uuid.UUID
    ) -> DocumentVerifyResult:
        document = await self._get_owned_document(organization_id, document_id)
        data = download_bytes(document.storage_key)
        recomputed = sha256_hash(data)
        return DocumentVerifyResult(
            sha256_hash=document.sha256_hash,
            recomputed_hash=recomputed,
            matches=recomputed == document.sha256_hash,
            verified_at=datetime.now(UTC),
        )

    async def invalidate(
        self,
        organization_id: uuid.UUID,
        document_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        reason: str,
    ) -> ConsentDocument:
        document = await self._get_owned_document(organization_id, document_id)
        if document.invalidated_at is not None:
            raise ConflictError(f"Document {document_id} is already invalidated")
        document.invalidated_at = datetime.now(UTC)
        document.invalidated_reason = reason
        document.invalidated_by_user_id = actor_user_id
        return document

    async def request_regeneration(
        self,
        organization_id: uuid.UUID,
        document_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        reason: str,
    ) -> None:
        # The actual PDF regeneration happens asynchronously in the worker
        # (see apps/worker/.../activities/generate_pdf.py) — this just
        # authorizes the request, resolves it down to the submission the
        # worker needs, and hands off via the outbox, same
        # write-then-async-consume split every other workflow in this
        # codebase uses (see consent.submitted).
        document = await self._get_owned_document(organization_id, document_id)
        submission = await self.repository.get_submission(document.submission_id)
        if submission is None:
            raise NotFoundError("ConsentSubmission", document.submission_id)
        await enqueue_event(
            self.session,
            organization_id=organization_id,
            event_type="consent.document.regenerate_requested",
            payload={
                "consent_request_id": str(submission.consent_request_id),
                "submission_id": str(document.submission_id),
                "reason": reason,
                "requested_by_user_id": str(actor_user_id),
            },
        )
