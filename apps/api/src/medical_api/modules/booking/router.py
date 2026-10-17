import uuid
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from medical_api.api.dependencies import AuthenticatedUser, DbSession
from medical_api.core.exceptions import ConflictError, NotFoundError, RateLimitedError
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
    PublicAppointmentConfirmation,
    PublicAppointmentCreate,
    PublicPractitionerRead,
    PublicTreatmentRead,
)
from medical_api.modules.booking.service import (
    BookingRequestService,
    book_public_appointment,
    resolve_public_organization,
)
from medical_api.modules.identity.repository import UserRepository
from medical_api.modules.scheduling.repository import (
    AppointmentRepository,
    AvailabilityRepository,
    PractitionerRepository,
)
from medical_api.modules.scheduling.schemas import AvailableSlot
from medical_api.modules.scheduling.service import AvailabilityService, PractitionerService
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
    """Published services, including the price and image managed by the owner."""
    organization = await resolve_public_organization(session)
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

    organization = await resolve_public_organization(session)
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


@public_router.get("/practitioners", response_model=list[PublicPractitionerRead])
async def list_public_practitioners(session: DbSession) -> list[PublicPractitionerRead]:
    organization = await resolve_public_organization(session)
    if organization is None:
        return []
    service = PractitionerService(PractitionerRepository(session), UserRepository(session))
    workers = await service.list_active(organization.id)
    return [
        PublicPractitionerRead(id=worker.id, full_name=worker.full_name, specialty=worker.specialty)
        for worker in workers
    ]


@public_router.get("/availability", response_model=list[AvailableSlot])
async def list_public_availability(
    session: DbSession,
    practitioner_id: uuid.UUID,
    treatment_definition_id: uuid.UUID,
    date_from: date,
    date_to: date,
) -> list[AvailableSlot]:
    organization = await resolve_public_organization(session)
    if organization is None:
        return []
    treatment = await TreatmentDefinitionRepository(session).get(
        organization.id, treatment_definition_id
    )
    if treatment is None or not treatment.is_active:
        raise NotFoundError("TreatmentDefinition", treatment_definition_id)
    practitioner = await PractitionerRepository(session).get(organization.id, practitioner_id)
    if practitioner is None or not practitioner.is_active:
        raise NotFoundError("Practitioner", practitioner_id)
    service = AvailabilityService(AvailabilityRepository(session), AppointmentRepository(session))
    return await service.compute_slots(
        organization.id, practitioner_id, date_from, date_to, treatment.duration_minutes
    )


@public_router.post("/appointments", response_model=PublicAppointmentConfirmation, status_code=201)
async def create_public_appointment(
    payload: PublicAppointmentCreate, session: DbSession
) -> PublicAppointmentConfirmation:
    ip_address = get_ip_address()
    if not await check_rate_limit(
        f"public_appointment:{ip_address or 'unknown'}", limit=5, window_seconds=3600
    ):
        raise RateLimitedError("Too many booking attempts. Please try again later.")
    organization = await resolve_public_organization(session)
    if organization is None:
        raise ConflictError("Online booking is not available. Please contact the clinic.")
    confirmation = await book_public_appointment(session, organization.id, payload)
    await AuditService(session).record(
        organization_id=organization.id,
        actor_user_id=None,
        action="appointment.booked_online",
        resource_type="appointment",
        resource_id=str(confirmation.id),
    )
    await session.commit()
    return confirmation
