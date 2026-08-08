import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from medical_api.modules.patients.models import EmergencyContact, Patient, PatientContact


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


class _PatientScopedRepository[ModelT: (PatientContact, EmergencyContact)]:
    """Same join-through-Patient pattern as medical_records' equivalent base
    (neither of these models carries its own organization_id) — kept
    separate rather than shared across modules since patients doesn't
    depend on medical_records and shouldn't start to just for this.
    """

    model: type[ModelT]

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_for_patient(
        self, organization_id: uuid.UUID, patient_id: uuid.UUID
    ) -> list[ModelT]:
        stmt = (
            select(self.model)
            .join(Patient, Patient.id == self.model.patient_id)
            .where(
                self.model.patient_id == patient_id,
                Patient.organization_id == organization_id,
            )
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get(self, organization_id: uuid.UUID, entry_id: uuid.UUID) -> ModelT | None:
        stmt = (
            select(self.model)
            .join(Patient, Patient.id == self.model.patient_id)
            .where(self.model.id == entry_id, Patient.organization_id == organization_id)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def create(self, entry: ModelT) -> ModelT:
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def delete(self, entry: ModelT) -> None:
        await self.session.delete(entry)
        await self.session.flush()


class PatientContactRepository(_PatientScopedRepository[PatientContact]):
    model = PatientContact


class EmergencyContactRepository(_PatientScopedRepository[EmergencyContact]):
    model = EmergencyContact
