import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from medical_api.modules.medical_records.models import ClinicalNote


class ClinicalNoteRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_for_patient(self, patient_id: uuid.UUID) -> list[ClinicalNote]:
        stmt = (
            select(ClinicalNote)
            .where(ClinicalNote.patient_id == patient_id)
            .order_by(ClinicalNote.created_at.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get(self, note_id: uuid.UUID) -> ClinicalNote | None:
        return await self.session.get(ClinicalNote, note_id)

    async def create(self, note: ClinicalNote) -> ClinicalNote:
        self.session.add(note)
        await self.session.flush()
        return note
