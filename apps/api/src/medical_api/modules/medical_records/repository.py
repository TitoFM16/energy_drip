import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from medical_api.modules.medical_records.models import ClinicalNote
from medical_api.modules.patients.models import Patient


class ClinicalNoteRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_for_patient(
        self, organization_id: uuid.UUID, patient_id: uuid.UUID
    ) -> list[ClinicalNote]:
        # ClinicalNote has no organization_id of its own — it's scoped
        # through the patient it belongs to, so the org check has to join.
        stmt = (
            select(ClinicalNote)
            .join(Patient, Patient.id == ClinicalNote.patient_id)
            .where(
                ClinicalNote.patient_id == patient_id,
                Patient.organization_id == organization_id,
            )
            .order_by(ClinicalNote.created_at.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get(self, organization_id: uuid.UUID, note_id: uuid.UUID) -> ClinicalNote | None:
        stmt = (
            select(ClinicalNote)
            .join(Patient, Patient.id == ClinicalNote.patient_id)
            .where(ClinicalNote.id == note_id, Patient.organization_id == organization_id)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def create(self, note: ClinicalNote) -> ClinicalNote:
        self.session.add(note)
        await self.session.flush()
        return note
