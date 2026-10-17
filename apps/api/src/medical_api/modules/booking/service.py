import uuid
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from medical_api.core.config import get_settings
from medical_api.core.exceptions import ConflictError, NotFoundError
from medical_api.modules.booking.models import BookingRequest
from medical_api.modules.booking.repository import BookingRequestRepository
from medical_api.modules.booking.schemas import (
    BookingRequestCreate,
    BookingRequestStatusUpdate,
    PublicAppointmentConfirmation,
    PublicAppointmentCreate,
)
from medical_api.modules.organizations.models import Organization
from medical_api.modules.patients.models import Patient
from medical_api.modules.patients.repository import PatientRepository
from medical_api.modules.scheduling.models import AppointmentStatus
from medical_api.modules.scheduling.repository import AppointmentRepository
from medical_api.modules.scheduling.schemas import AppointmentCreate
from medical_api.modules.scheduling.service import AppointmentService
from medical_api.modules.treatments.repository import TreatmentDefinitionRepository


class BookingRequestService:
    def __init__(
        self,
        repository: BookingRequestRepository,
        treatment_definitions: TreatmentDefinitionRepository,
    ):
        self.repository = repository
        self.treatment_definitions = treatment_definitions

    async def create_request(
        self, organization_id: uuid.UUID, data: BookingRequestCreate, ip_address: str | None
    ) -> BookingRequest | None:
        """Returns None for a honeypot-triggered submission. The caller
        must still respond with the normal success message either way —
        confirming the filter to an automated submitter would just teach
        it to leave the field blank next time.
        """
        if data.website:
            return None
        definition = await self.treatment_definitions.get(
            organization_id, data.treatment_definition_id
        )
        if definition is None or not definition.is_active:
            raise NotFoundError("TreatmentDefinition", data.treatment_definition_id)
        booking_request = BookingRequest(
            organization_id=organization_id,
            treatment_definition_id=data.treatment_definition_id,
            first_name=data.first_name,
            last_name=data.last_name,
            phone_number=data.phone_number,
            email=data.email,
            preferred_date=data.preferred_date,
            message=data.message,
            ip_address=ip_address,
        )
        return await self.repository.create(booking_request)

    async def list_all(self, organization_id: uuid.UUID) -> list[BookingRequest]:
        return await self.repository.list_all(organization_id)

    async def update_status(
        self,
        organization_id: uuid.UUID,
        booking_request_id: uuid.UUID,
        data: BookingRequestStatusUpdate,
    ) -> BookingRequest:
        booking_request = await self.repository.get(organization_id, booking_request_id)
        if booking_request is None:
            raise NotFoundError("BookingRequest", booking_request_id)
        booking_request.status = data.status
        return booking_request


async def resolve_public_organization(session: AsyncSession) -> Organization | None:
    """Never choose an arbitrary clinic when a deployment contains multiple clinics."""
    stmt = select(Organization).where(Organization.is_active.is_(True))
    configured_id = get_settings().public_organization_id
    if configured_id is not None:
        stmt = stmt.where(Organization.id == configured_id)
    organizations = list((await session.execute(stmt.limit(2))).scalars())
    return organizations[0] if len(organizations) == 1 else None


async def book_public_appointment(
    session: AsyncSession, organization_id: uuid.UUID, data: PublicAppointmentCreate
) -> PublicAppointmentConfirmation:
    if data.website:
        raise ConflictError("Unable to process this booking")
    treatment = await TreatmentDefinitionRepository(session).get(
        organization_id, data.treatment_definition_id
    )
    if treatment is None or not treatment.is_active:
        raise NotFoundError("TreatmentDefinition", data.treatment_definition_id)
    # An anonymous caller cannot update or attach themselves to an existing
    # patient's clinical record merely by knowing that patient's phone number.
    patient = await PatientRepository(session).create(
        Patient(
            organization_id=organization_id,
            first_name=data.first_name,
            last_name=data.last_name,
            phone_number=data.phone_number,
            email=data.email,
        )
    )
    service = AppointmentService(AppointmentRepository(session), session)
    appointment = await service.schedule(
        organization_id,
        AppointmentCreate(
            patient_id=patient.id,
            practitioner_id=data.practitioner_id,
            treatment_definition_id=treatment.id,
            starts_at=data.starts_at,
            ends_at=data.starts_at + timedelta(minutes=treatment.duration_minutes),
            notes=data.message,
        ),
    )
    appointment = await service.change_status(
        organization_id, appointment.id, AppointmentStatus.CONFIRMED, "Reserva en línea"
    )
    read = await service.to_read(appointment)
    return PublicAppointmentConfirmation(
        id=appointment.id,
        starts_at=appointment.starts_at,
        ends_at=appointment.ends_at,
        status=appointment.status,
        treatment_name=treatment.name,
        practitioner_name=read.practitioner_name or "",
        detail="Tu cita está confirmada. Guarda estos datos para tu visita.",
    )
