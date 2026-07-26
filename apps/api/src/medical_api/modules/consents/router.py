import uuid

from fastapi import APIRouter, Depends, Request

from medical_api.api.dependencies import AuthenticatedUser, DbSession
from medical_api.core.security import require_roles
from medical_api.modules.consents.repository import ConsentRepository
from medical_api.modules.consents.schemas import (
    ConsentFormRead,
    ConsentSubmissionCreate,
    ConsentSubmissionResult,
)
from medical_api.modules.consents.service import ConsentService

# Mounted under /api/v1/consents (staff, authenticated) and
# /api/v1/public/consents (patient, token-based).
router = APIRouter()
public_router = APIRouter()


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
    the raw token returned here is what gets embedded in the SMS/WhatsApp link.
    """
    service = ConsentService(ConsentRepository(session), session)
    request, raw_token = await service.create_request(
        user.organization_id, patient_id, appointment_id, template_version_id
    )
    await session.commit()
    return {"consent_request_id": str(request.id), "token": raw_token}


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
