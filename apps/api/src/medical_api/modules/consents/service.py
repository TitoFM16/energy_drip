import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from medical_api.core.exceptions import ConflictError, NotFoundError
from medical_api.integrations.object_storage.client import (
    download_bytes,
    generate_presigned_download_url,
    upload_bytes,
)
from medical_api.integrations.pdf.generator import render_consent_pdf
from medical_api.modules.audit.service import AuditService
from medical_api.modules.consents.models import (
    ConsentAnswer,
    ConsentDocument,
    ConsentEvent,
    ConsentQuestion,
    ConsentQuestionOption,
    ConsentRequest,
    ConsentRequestStatus,
    ConsentReviewDecision,
    ConsentSignature,
    ConsentSubmission,
    ConsentTemplate,
    ConsentTemplateVersion,
    EligibilityResult,
)
from medical_api.modules.consents.repository import ConsentRepository, ConsentTemplateRepository
from medical_api.modules.consents.schemas import (
    ConsentAnswerRead,
    ConsentFormRead,
    ConsentQuestionPublic,
    ConsentRequestDetail,
    ConsentSubmissionCreate,
    ConsentSubmissionRead,
    ConsentSubmissionReviewCreate,
    ConsentTemplateCreate,
    ConsentTemplateRead,
    DocumentVerifyResult,
)
from medical_api.modules.consents.validation import validate_submission_answers
from medical_api.modules.patients.repository import PatientRepository
from medical_api.modules.scheduling.repository import AppointmentRepository
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
        if await PatientRepository(self.session).get(organization_id, patient_id) is None:
            raise NotFoundError("Patient", patient_id)
        version = await self.repository.get_template_version(template_version_id)
        template = (
            await ConsentTemplateRepository(self.session).get_template(
                organization_id, version.template_id
            )
            if version
            else None
        )
        if template is None or not template.is_active or version.published_at is None:
            raise NotFoundError("PublishedConsentTemplate", template_version_id)
        if appointment_id is not None:
            appointment = await AppointmentRepository(self.session).get(
                organization_id, appointment_id
            )
            if appointment is None or appointment.patient_id != patient_id:
                raise NotFoundError("Appointment", appointment_id)
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
        await run_in_threadpool(
            upload_bytes, signature_key, sanitized_signature_svg.encode(), "image/svg+xml"
        )
        self.session.add(
            ConsentSignature(submission_id=submission.id, signature_svg_path=signature_key)
        )

        request.status = ConsentRequestStatus.COMPLETED
        self.session.add(
            ConsentEvent(
                consent_request_id=request.id, event_type="consent.submitted", event_metadata={}
            )
        )

        await self.session.flush()
        await DocumentService(self.repository, self.session).generate(submission.id)
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
            reviewed_by_name = (
                await self.repository.get_user_full_name(submission.reviewed_by_user_id)
                if submission.reviewed_by_user_id is not None
                else None
            )
            submission_read = ConsentSubmissionRead(
                id=submission.id,
                submitted_at=submission.submitted_at,
                timezone=submission.timezone,
                eligibility_result=submission.eligibility_result,
                review_decision=submission.review_decision,
                review_rationale=submission.review_rationale,
                reviewed_by_user_id=submission.reviewed_by_user_id,
                reviewed_by_name=reviewed_by_name,
                reviewed_at=submission.reviewed_at,
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

    async def review_submission(
        self,
        organization_id: uuid.UUID,
        submission_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        data: ConsentSubmissionReviewCreate,
    ) -> ConsentSubmission:
        submission = await self.repository.get_submission_with_org_check(
            organization_id, submission_id, for_update=True
        )
        if submission is None:
            raise NotFoundError("ConsentSubmission", submission_id)
        if submission.eligibility_result != EligibilityResult.REQUIRES_MANUAL_REVIEW:
            raise ConflictError("Only submissions requiring manual review can be reviewed")
        if submission.review_decision is not None:
            raise ConflictError(f"Consent submission {submission_id} has already been reviewed")

        submission.review_decision = ConsentReviewDecision(data.decision)
        submission.review_rationale = data.rationale
        submission.reviewed_by_user_id = actor_user_id
        submission.reviewed_at = datetime.now(UTC)
        await self.session.flush()
        return submission


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
        data = await run_in_threadpool(download_bytes, document.storage_key)
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
        document = await self._get_owned_document(organization_id, document_id)
        await self.generate(document.submission_id, reason=reason, actor_user_id=actor_user_id)

    async def generate(
        self,
        submission_id: uuid.UUID,
        *,
        reason: str | None = None,
        actor_user_id: uuid.UUID | None = None,
    ) -> ConsentDocument:
        submission = await self.repository.get_submission(submission_id)
        if submission is None:
            raise NotFoundError("ConsentSubmission", submission_id)
        request = await self.repository.get_request(submission.consent_request_id)
        # Serialize regeneration as well as submission so only one current version exists.
        await self.repository.get_submission_with_org_check(
            request.organization_id, submission_id, for_update=True
        )
        current = await self.repository.get_current_document_for_submission(submission_id)
        signature = await self.repository.get_signature(submission_id)
        if signature is None:
            raise ConflictError("The signed record has no signature to render")
        version = await self.repository.get_template_version(request.template_version_id)
        patient = await PatientRepository(self.session).get(
            request.organization_id, request.patient_id
        )
        answers = await self.repository.list_answers(submission_id)
        signature_svg = await run_in_threadpool(download_bytes, signature.signature_svg_path)
        pdf = await run_in_threadpool(
            render_consent_pdf,
            patient_name=f"{patient.first_name} {patient.last_name}",
            template_body_markdown=version.body_markdown,
            answers=[{"field_key": a.field_key, "value": a.value.get("value")} for a in answers],
            signature_svg=signature_svg.decode(),
            signed_at=submission.submitted_at,
            ip_address=submission.ip_address,
        )
        key = (
            f"organizations/{request.organization_id}/patients/{request.patient_id}/"
            f"consents/{request.id}/{uuid.uuid4()}.pdf"
        )
        await run_in_threadpool(upload_bytes, key, pdf, "application/pdf")
        prior = await self.repository.list_documents_for_submission(submission_id)
        if current is not None:
            current.is_current = False
        version_number = max((d.document_version for d in prior), default=0) + 1
        document = await self.repository.create_document(
            ConsentDocument(
                submission_id=submission_id,
                storage_key=key,
                sha256_hash=sha256_hash(pdf),
                document_version=version_number,
                regenerated_reason=reason,
            )
        )
        await AuditService(self.session).record(
            organization_id=request.organization_id,
            actor_user_id=actor_user_id,
            action="document.created" if version_number == 1 else "document.regenerated",
            resource_type="consent_document",
            resource_id=str(document.id),
            metadata={"document_version": version_number},
        )
        return document
