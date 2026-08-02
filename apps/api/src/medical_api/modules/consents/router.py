import uuid

from fastapi import APIRouter, Depends, Request

from medical_api.api.dependencies import AuthenticatedUser, DbSession
from medical_api.core.exceptions import NotFoundError
from medical_api.core.security import require_roles
from medical_api.modules.consents.repository import ConsentRepository, ConsentTemplateRepository
from medical_api.modules.consents.schemas import (
    ConsentFormRead,
    ConsentQuestionPublic,
    ConsentRequestDetail,
    ConsentRequestRead,
    ConsentSubmissionCreate,
    ConsentSubmissionResult,
    ConsentTemplateCreate,
    ConsentTemplateRead,
    ConsentTemplateVersionDetail,
    ConsentTemplateVersionRead,
)
from medical_api.modules.consents.service import ConsentService, ConsentTemplateService

# Mounted under /api/v1/consents (staff, authenticated) and
# /api/v1/public/consents (patient, token-based).
router = APIRouter()
public_router = APIRouter()


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
    await session.commit()
    return {"consent_request_id": str(request.id), "token": raw_token}


@router.get("/requests", response_model=list[ConsentRequestRead])
async def list_consent_requests(
    user: AuthenticatedUser, session: DbSession, patient_id: uuid.UUID | None = None
) -> list[ConsentRequestRead]:
    service = ConsentService(ConsentRepository(session), session)
    return await service.list_requests(user.organization_id, patient_id)


@router.get("/requests/{request_id}", response_model=ConsentRequestDetail)
async def get_consent_request(
    request_id: uuid.UUID, user: AuthenticatedUser, session: DbSession
) -> ConsentRequestDetail:
    service = ConsentService(ConsentRepository(session), session)
    return await service.get_request_detail(user.organization_id, request_id)


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
