import uuid
from datetime import UTC, datetime

from medical_api.core.exceptions import ConflictError, NotFoundError
from medical_api.modules.medical_records.models import ClinicalNote
from medical_api.modules.medical_records.repository import ClinicalNoteRepository
from medical_api.modules.medical_records.schemas import ClinicalNoteCreate


class ClinicalNoteService:
    def __init__(self, repository: ClinicalNoteRepository):
        self.repository = repository

    async def add_note(self, author_user_id: uuid.UUID, data: ClinicalNoteCreate) -> ClinicalNote:
        note = ClinicalNote(author_user_id=author_user_id, **data.model_dump())
        return await self.repository.create(note)

    async def finalize(self, note_id: uuid.UUID) -> ClinicalNote:
        note = await self.repository.get(note_id)
        if note is None:
            raise NotFoundError("ClinicalNote", note_id)
        if note.is_finalized:
            raise ConflictError(f"Clinical note {note_id} is already finalized")
        note.is_finalized = True
        note.finalized_at = datetime.now(UTC)
        return note

    async def history(self, patient_id: uuid.UUID) -> list[ClinicalNote]:
        return await self.repository.list_for_patient(patient_id)
