import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from medical_api.modules.booking.models import BookingRequest


class BookingRequestRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, booking_request: BookingRequest) -> BookingRequest:
        self.session.add(booking_request)
        await self.session.flush()
        return booking_request

    async def list_all(self, organization_id: uuid.UUID) -> list[BookingRequest]:
        stmt = (
            select(BookingRequest)
            .where(BookingRequest.organization_id == organization_id)
            .order_by(BookingRequest.created_at.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get(
        self, organization_id: uuid.UUID, booking_request_id: uuid.UUID
    ) -> BookingRequest | None:
        stmt = select(BookingRequest).where(
            BookingRequest.id == booking_request_id,
            BookingRequest.organization_id == organization_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()
