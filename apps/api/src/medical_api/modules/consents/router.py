import uuid

from fastapi import APIRouter, Depends, Request

from medical_api.api.dependencies import AuthenticatedUser, DbSession
from medical_api.core.exceptions import NotFoundError
from medical_api.core.security import require_roles
from medical_api.modules.audit.service import AuditService
from medical_api.modules.consents.models import ConsentRequestStatus
from medical_api.modules.consents.repository import ConsentRepository, ConsentTemplateRepository
from medical_api.modules.consents.schemas import (
    ConsentFormRead,
    ConsentQuestionPublic,
    ConsentRequestDetail,
    ConsentRequestInvalidate,
    ConsentRequestRead,
    ConsentSubmissionCreate,
    ConsentSubmissionResult,
    ConsentSubmissionReviewCreate,
    ConsentSubmissionReviewRead,
    ConsentTemplateCreate,
    ConsentTemplateRead,
    ConsentTemplateVersionDetail,
    ConsentTemplateVersionRead,
    DocumentDownloadRead,
    DocumentInvalidate,
    DocumentRead,
    DocumentRegenerate,
    DocumentVerifyResult,
)
from medical_api.modules.consents.service import (
    ConsentService,
    ConsentTemplateService,
    DocumentService,
)

# Mounted under /api/v1/consents (staff, authenticated),
# /api/v1/public/consents (patient, token-based), and
# /api/v1/documents (staff, authenticated).
router = APIRouter()
public_router = APIRouter()
documents_router = APIRouter()

# Signed consent PDFs are restricted clinical/legal content — same
# reasoning as clinical notes (reception/assistant can schedule around
# them but shouldn't read them). Invalidating one is a bigger, more
# deliberate action than reading or downloading it, so it's held to a
# tighter set of roles than metadata/download/verify.
_DOCUMENT_READ_ROLES = ("organization_admin", "medical_director", "practitioner")
_DOCUMENT_ADMIN_ROLES = ("organization_admin", "medical_director")
_SUBMISSION_REVIEW_ROLES = ("organization_admin", "medical_director", "practitioner")


@router.post(
    "/templates",
    response_model=ConsentTemplateRead,
    status_code=201,
    dependencies=[Depends(require_roles("organization_admin", "medical_director"))],
)
async def create_consent_template(
    payload: ConsentTemplateCreate, user: AuthenticatedUser, session: DbSession
) -> ConsentTemplateRead:
    service = ConsentTemplateService(ConsentTemplateRepository(session))
    template = await service.create(user.organization_id, payload)
    await AuditService(session).record(
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        action="consent_template.created",
        resource_type="consent_template",
        resource_id=str(template.id),
    )
    await session.commit()
    return template


@router.get("/templates", response_model=list[ConsentTemplateRead])
async def list_consent_templates(
    user: AuthenticatedUser, session: DbSession
) -> list[ConsentTemplateRead]:
    service = ConsentTemplateService(ConsentTemplateRepository(session))
    return await service.list_all(user.organization_id)


@router.post(
    "/templates/{template_id}/versions/{version_id}/publish",
    response_model=ConsentTemplateVersionRead,
    dependencies=[Depends(require_roles("organization_admin", "medical_director"))],
)
async def publish_consent_template_version(
    template_id: uuid.UUID, version_id: uuid.UUID, user: AuthenticatedUser, session: DbSession
) -> ConsentTemplateVersionRead:
    service = ConsentTemplateService(ConsentTemplateRepository(session))
    version = await service.publish_version(user.organization_id, template_id, version_id)
    await AuditService(session).record(
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        action="consent_template_version.published",
        resource_type="consent_template_version",
        resource_id=str(version.id),
        metadata={"template_id": str(template_id)},
    )
    await session.commit()
    return version


@router.get("/templates/versions/{version_id}", response_model=ConsentTemplateVersionDetail)
async def get_consent_template_version(
    version_id: uuid.UUID, user: AuthenticatedUser, session: DbSession
) -> ConsentTemplateVersionDetail:
    """Staff-side full content of a version, independent of consent-request
    status — used both to preview a draft before publishing and to review
    the exact questions a patient answered on a completed submission.
    """
    template_repository = ConsentTemplateRepository(session)
    version = await template_repository.get_version(version_id)
    if version is None:
        raise NotFoundError("ConsentTemplateVersion", version_id)
    template = await template_repository.get_template(user.organization_id, version.template_id)
    if template is None:
        raise NotFoundError("ConsentTemplateVersion", version_id)

    consent_repository = ConsentRepository(session)
    questions = await consent_repository.list_questions(version_id)
    question_payloads = []
    for question in questions:
        options = await consent_repository.list_options(question.id)
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
    return ConsentTemplateVersionDetail(
        id=version.id,
        template_id=version.template_id,
        version_number=version.version_number,
        published_at=version.published_at,
        body_markdown=version.body_markdown,
        questions=question_payloads,
    )


@router.post(
    "/requests",
    status_code=201,
    dependencies=[
        Depends(require_roles("receptionist", "assistant", "practitioner", "organization_admin"))
    ],
)
async def create_consent_request(
    patient_id: uuid.UUID,
    template_version_id: uuid.UUID,
    user: AuthenticatedUser,
    session: DbSession,
    appointment_id: uuid.UUID | None = None,
) -> dict[str, str]:
    """Creates a single-use consent link. Only the token hash is persisted —
    the raw token returned here is what gets embedded in the WhatsApp link.
    """
    service = ConsentService(ConsentRepository(session), session)
    request, raw_token = await service.create_request(
        user.organization_id, patient_id, appointment_id, template_version_id
    )
    await AuditService(session).record(
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        action="consent_request.created",
        resource_type="consent_request",
        resource_id=str(request.id),
        metadata={"patient_id": str(patient_id)},
    )
    await session.commit()
    return {"consent_request_id": str(request.id), "token": raw_token}


@router.get("/requests", response_model=list[ConsentRequestRead])
async def list_consent_requests(
    user: AuthenticatedUser,
    session: DbSession,
    patient_id: uuid.UUID | None = None,
    status: ConsentRequestStatus | None = None,
    needs_review: bool = False,
) -> list[ConsentRequestRead]:
    service = ConsentService(ConsentRepository(session), session)
    return await service.list_requests(
        user.organization_id,
        patient_id,
        status=status,
        needs_review=needs_review,
    )


@router.get("/requests/{request_id}", response_model=ConsentRequestDetail)
async def get_consent_request(
    request_id: uuid.UUID, user: AuthenticatedUser, session: DbSession
) -> ConsentRequestDetail:
    service = ConsentService(ConsentRepository(session), session)
    return await service.get_request_detail(user.organization_id, request_id)


@router.post(
    "/submissions/{submission_id}/review",
    response_model=ConsentSubmissionReviewRead,
    dependencies=[Depends(require_roles(*_SUBMISSION_REVIEW_ROLES))],
)
async def review_consent_submission(
    submission_id: uuid.UUID,
    payload: ConsentSubmissionReviewCreate,
    user: AuthenticatedUser,
    session: DbSession,
) -> ConsentSubmissionReviewRead:
    repository = ConsentRepository(session)
    service = ConsentService(repository, session)
    submission = await service.review_submission(
        user.organization_id,
        submission_id,
        user.user_id,
        payload,
    )
    await AuditService(session).record(
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        action="consent_submission.reviewed",
        resource_type="consent_submission",
        resource_id=str(submission.id),
        metadata={"decision": payload.decision, "rationale": payload.rationale},
    )
    reviewed_by_name = await repository.get_user_full_name(user.user_id)
    await session.commit()
    return ConsentSubmissionReviewRead(
        decision=submission.review_decision,
        rationale=submission.review_rationale,
        reviewed_by_user_id=submission.reviewed_by_user_id,
        reviewed_by_name=reviewed_by_name or "Usuario",
        reviewed_at=submission.reviewed_at,
    )


@router.post(
    "/requests/{request_id}/invalidate",
    response_model=ConsentRequestRead,
    dependencies=[
        Depends(require_roles("receptionist", "assistant", "practitioner", "organization_admin"))
    ],
)
async def invalidate_consent_request(
    request_id: uuid.UUID,
    payload: ConsentRequestInvalidate,
    user: AuthenticatedUser,
    session: DbSession,
) -> ConsentRequestRead:
    service = ConsentService(ConsentRepository(session), session)
    request = await service.invalidate_request(user.organization_id, request_id, payload.reason)
    await AuditService(session).record(
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        action="consent_request.invalidated",
        resource_type="consent_request",
        resource_id=str(request.id),
        metadata={"reason": payload.reason},
    )
    await session.commit()
    return request


@router.post(
    "/requests/{request_id}/resend",
    status_code=201,
    dependencies=[
        Depends(require_roles("receptionist", "assistant", "practitioner", "organization_admin"))
    ],
)
async def resend_consent_request(
    request_id: uuid.UUID, user: AuthenticatedUser, session: DbSession
) -> dict[str, str]:
    """Same response shape as create_consent_request: only the raw token is
    ever returned over the wire, never persisted (see ConsentRequest's
    docstring) — the caller embeds it in a fresh WhatsApp link.
    """
    service = ConsentService(ConsentRepository(session), session)
    new_request, raw_token = await service.resend_request(user.organization_id, request_id)
    await AuditService(session).record(
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        action="consent_request.resent",
        resource_type="consent_request",
        resource_id=str(new_request.id),
        metadata={"original_request_id": str(request_id)},
    )
    await session.commit()
    return {"consent_request_id": str(new_request.id), "token": raw_token}


@public_router.get("/{token}", response_model=ConsentFormRead)
async def get_consent_form(token: str, session: DbSession) -> ConsentFormRead:
    service = ConsentService(ConsentRepository(session), session)
    return await service.get_form(token)


@public_router.post("/{token}/submit", response_model=ConsentSubmissionResult, status_code=201)
async def submit_consent_form(
    token: str, payload: ConsentSubmissionCreate, request: Request, session: DbSession
) -> ConsentSubmissionResult:
    service = ConsentService(ConsentRepository(session), session)
    client_ip = request.client.host if request.client else "unknown"
    submission = await service.submit(
        token,
        payload,
        ip_address=client_ip,
        user_agent=request.headers.get("user-agent", "unknown"),
    )
    await session.commit()
    return ConsentSubmissionResult(
        submission_id=submission.id, eligibility_result=submission.eligibility_result
    )


@documents_router.get(
    "/{document_id}",
    response_model=DocumentRead,
    dependencies=[Depends(require_roles(*_DOCUMENT_READ_ROLES))],
)
async def get_document(
    document_id: uuid.UUID, user: AuthenticatedUser, session: DbSession
) -> DocumentRead:
    service = DocumentService(ConsentRepository(session), session)
    document = await service.get_metadata(user.organization_id, document_id)
    await AuditService(session).record(
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        action="document.accessed",
        resource_type="consent_document",
        resource_id=str(document.id),
    )
    await session.commit()
    return document


@documents_router.get(
    "/{document_id}/download",
    response_model=DocumentDownloadRead,
    dependencies=[Depends(require_roles(*_DOCUMENT_READ_ROLES))],
)
async def download_document(
    document_id: uuid.UUID, user: AuthenticatedUser, session: DbSession
) -> DocumentDownloadRead:
    service = DocumentService(ConsentRepository(session), session)
    url, expires_in = await service.get_download_url(user.organization_id, document_id)
    await AuditService(session).record(
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        action="document.downloaded",
        resource_type="consent_document",
        resource_id=str(document_id),
    )
    await session.commit()
    return DocumentDownloadRead(url=url, expires_in=expires_in)


@documents_router.post(
    "/{document_id}/verify",
    response_model=DocumentVerifyResult,
    dependencies=[Depends(require_roles(*_DOCUMENT_READ_ROLES))],
)
async def verify_document(
    document_id: uuid.UUID, user: AuthenticatedUser, session: DbSession
) -> DocumentVerifyResult:
    service = DocumentService(ConsentRepository(session), session)
    result = await service.verify(user.organization_id, document_id)
    await AuditService(session).record(
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        action="document.verified",
        resource_type="consent_document",
        resource_id=str(document_id),
        metadata={"matches": result.matches},
    )
    await session.commit()
    return result


@documents_router.post(
    "/{document_id}/invalidate",
    response_model=DocumentRead,
    dependencies=[Depends(require_roles(*_DOCUMENT_ADMIN_ROLES))],
)
async def invalidate_document(
    document_id: uuid.UUID,
    payload: DocumentInvalidate,
    user: AuthenticatedUser,
    session: DbSession,
) -> DocumentRead:
    service = DocumentService(ConsentRepository(session), session)
    document = await service.invalidate(
        user.organization_id, document_id, user.user_id, payload.reason
    )
    await AuditService(session).record(
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        action="document.invalidated",
        resource_type="consent_document",
        resource_id=str(document.id),
        metadata={"reason": payload.reason},
    )
    await session.commit()
    return document


@documents_router.post(
    "/{document_id}/regenerate",
    status_code=202,
    dependencies=[Depends(require_roles(*_DOCUMENT_ADMIN_ROLES))],
)
async def regenerate_document(
    document_id: uuid.UUID,
    payload: DocumentRegenerate,
    user: AuthenticatedUser,
    session: DbSession,
) -> dict[str, str]:
    service = DocumentService(ConsentRepository(session), session)
    await service.request_regeneration(
        user.organization_id, document_id, user.user_id, payload.reason
    )
    await AuditService(session).record(
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        action="document.regeneration_requested",
        resource_type="consent_document",
        resource_id=str(document_id),
        metadata={"reason": payload.reason},
    )
    await session.commit()
    return {"status": "regeneration_requested"}
