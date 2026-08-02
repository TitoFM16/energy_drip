import uuid

from medical_api.core.exceptions import NotFoundError
from medical_api.modules.booking.models import BookingRequest
from medical_api.modules.booking.repository import BookingRequestRepository
from medical_api.modules.booking.schemas import BookingRequestCreate, BookingRequestStatusUpdate
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
