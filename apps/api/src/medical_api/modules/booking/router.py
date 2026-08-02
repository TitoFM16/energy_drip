import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from medical_api.api.dependencies import AuthenticatedUser, DbSession
from medical_api.core.exceptions import RateLimitedError
from medical_api.core.rate_limit import check_rate_limit
from medical_api.core.request_context import get_ip_address
from medical_api.core.security import require_roles
from medical_api.modules.audit.service import AuditService
from medical_api.modules.booking.repository import BookingRequestRepository
from medical_api.modules.booking.schemas import (
    BookingRequestConfirmation,
    BookingRequestCreate,
    BookingRequestRead,
    BookingRequestStatusUpdate,
    PublicTreatmentRead,
)
from medical_api.modules.booking.service import BookingRequestService
from medical_api.modules.organizations.repository import OrganizationRepository
from medical_api.modules.treatments.repository import TreatmentDefinitionRepository

# Mounted under /api/v1/booking-requests (staff, authenticated) and
# /api/v1/public (public_router — anonymous, from the landing site's
# /reservar form).
router = APIRouter()
public_router = APIRouter()

_STAFF_ROLES = ("receptionist", "assistant", "practitioner", "organization_admin")

# Deliberately low: this is a marketing-site lead-capture form, not a
# booking calendar a legitimate user would hit repeatedly. Keyed by IP —
# see check_rate_limit's docstring for why this is a fixed window, not a
# precise one.
_BOOKING_REQUEST_RATE_LIMIT = 5
_BOOKING_REQUEST_RATE_WINDOW_SECONDS = 3600


def _build_service(session: AsyncSession) -> BookingRequestService:
    return BookingRequestService(
        BookingRequestRepository(session), TreatmentDefinitionRepository(session)
    )


@public_router.get("/treatments", response_model=list[PublicTreatmentRead])
async def list_public_treatments(session: DbSession) -> list[PublicTreatmentRead]:
    """Only what's safe for an anonymous visitor: active treatment names
    and descriptions. No pricing, session counts, or anything else
    internal — see "Connected public booking experience" in
    missing_features.md.
    """
    organization = await OrganizationRepository(session).get_first()
    if organization is None:
        return []
    repository = TreatmentDefinitionRepository(session)
    return await repository.list_all(organization.id, include_inactive=False)


@public_router.post("/booking-requests", response_model=BookingRequestConfirmation, status_code=201)
async def create_booking_request(
    payload: BookingRequestCreate, session: DbSession
) -> BookingRequestConfirmation:
    ip_address = get_ip_address()
    allowed = await check_rate_limit(
        f"booking_request:{ip_address or 'unknown'}",
        limit=_BOOKING_REQUEST_RATE_LIMIT,
        window_seconds=_BOOKING_REQUEST_RATE_WINDOW_SECONDS,
    )
    if not allowed:
        raise RateLimitedError("Too many booking requests. Please try again later.")

    organization = await OrganizationRepository(session).get_first()
    if organization is None:
        # Same response either way — nothing about clinic bootstrap state
        # should be observable from the public site.
        return BookingRequestConfirmation(
            detail="¡Gracias! Nos pondremos en contacto contigo pronto."
        )

    service = _build_service(session)
    await service.create_request(organization.id, payload, ip_address)
    await session.commit()
    return BookingRequestConfirmation(detail="¡Gracias! Nos pondremos en contacto contigo pronto.")


@router.get(
    "",
    response_model=list[BookingRequestRead],
    dependencies=[Depends(require_roles(*_STAFF_ROLES))],
)
async def list_booking_requests(
    user: AuthenticatedUser, session: DbSession
) -> list[BookingRequestRead]:
    service = _build_service(session)
    return await service.list_all(user.organization_id)


@router.patch(
    "/{booking_request_id}/status",
    response_model=BookingRequestRead,
    dependencies=[Depends(require_roles(*_STAFF_ROLES))],
)
async def update_booking_request_status(
    booking_request_id: uuid.UUID,
    payload: BookingRequestStatusUpdate,
    user: AuthenticatedUser,
    session: DbSession,
) -> BookingRequestRead:
    service = _build_service(session)
    booking_request = await service.update_status(user.organization_id, booking_request_id, payload)
    await AuditService(session).record(
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        action="booking_request.status_updated",
        resource_type="booking_request",
        resource_id=str(booking_request.id),
        metadata={"status": str(payload.status)},
    )
    await session.commit()
    return booking_request
