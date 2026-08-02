import uuid
from datetime import UTC, datetime

from medical_api.core.exceptions import ConflictError, NotFoundError
from medical_api.modules.medical_records.models import ClinicalNote
from medical_api.modules.medical_records.repository import ClinicalNoteRepository
from medical_api.modules.medical_records.schemas import ClinicalNoteCreate
from medical_api.modules.patients.repository import PatientRepository


class ClinicalNoteService:
    def __init__(self, repository: ClinicalNoteRepository, patients: PatientRepository):
        self.repository = repository
        self.patients = patients

    async def add_note(
        self, organization_id: uuid.UUID, author_user_id: uuid.UUID, data: ClinicalNoteCreate
    ) -> ClinicalNote:
        # ClinicalNoteCreate carries a caller-supplied patient_id — without
        # this check, any practitioner could attach a clinical note to a
        # patient in a different organization.
        patient = await self.patients.get(organization_id, data.patient_id)
        if patient is None:
            raise NotFoundError("Patient", data.patient_id)
        note = ClinicalNote(author_user_id=author_user_id, **data.model_dump())
        return await self.repository.create(note)

    async def finalize(self, organization_id: uuid.UUID, note_id: uuid.UUID) -> ClinicalNote:
        note = await self.repository.get(organization_id, note_id)
        if note is None:
            raise NotFoundError("ClinicalNote", note_id)
        if note.is_finalized:
            raise ConflictError(f"Clinical note {note_id} is already finalized")
        note.is_finalized = True
        note.finalized_at = datetime.now(UTC)
        return note

    async def history(
        self, organization_id: uuid.UUID, patient_id: uuid.UUID
    ) -> list[ClinicalNote]:
        return await self.repository.list_for_patient(organization_id, patient_id)
