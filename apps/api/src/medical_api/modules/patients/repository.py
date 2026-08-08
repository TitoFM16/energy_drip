import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from medical_api.modules.patients.models import Patient


class PatientRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, organization_id: uuid.UUID, patient_id: uuid.UUID) -> Patient | None:
        stmt = select(Patient).where(
            Patient.organization_id == organization_id, Patient.id == patient_id
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_by_phone_number(
        self, organization_id: uuid.UUID, phone_number: str
    ) -> Patient | None:
        digits = "".join(character for character in phone_number if character.isdigit())
        if not digits:
            return None
        stmt = select(Patient).where(
            Patient.organization_id == organization_id,
            func.regexp_replace(Patient.phone_number, r"\D", "", "g") == digits,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def search(
        self, organization_id: uuid.UUID, query: str | None, limit: int = 25
    ) -> list[Patient]:
        stmt = select(Patient).where(Patient.organization_id == organization_id)
        if query:
            like = f"%{query}%"
            stmt = stmt.where(
                or_(
                    Patient.first_name.ilike(like),
                    Patient.last_name.ilike(like),
                    Patient.document_id.ilike(like),
                )
            )
        stmt = stmt.order_by(Patient.last_name).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def create(self, patient: Patient) -> Patient:
        self.session.add(patient)
        await self.session.flush()
        return patient
