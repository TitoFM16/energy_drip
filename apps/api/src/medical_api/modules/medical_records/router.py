import uuid

from fastapi import APIRouter, Depends

from medical_api.api.dependencies import AuthenticatedUser, DbSession
from medical_api.core.security import require_roles
from medical_api.modules.medical_records.repository import ClinicalNoteRepository
from medical_api.modules.medical_records.schemas import ClinicalNoteCreate, ClinicalNoteRead
from medical_api.modules.medical_records.service import ClinicalNoteService

router = APIRouter()


@router.get("/{patient_id}/clinical-notes", response_model=list[ClinicalNoteRead])
async def list_clinical_notes(
    patient_id: uuid.UUID, user: AuthenticatedUser, session: DbSession
) -> list[ClinicalNoteRead]:
    service = ClinicalNoteService(ClinicalNoteRepository(session))
    return await service.history(patient_id)


@router.post(
    "/clinical-notes",
    response_model=ClinicalNoteRead,
    status_code=201,
    dependencies=[Depends(require_roles("practitioner", "medical_director"))],
)
async def create_clinical_note(
    payload: ClinicalNoteCreate, user: AuthenticatedUser, session: DbSession
) -> ClinicalNoteRead:
    service = ClinicalNoteService(ClinicalNoteRepository(session))
    note = await service.add_note(user.user_id, payload)
    await session.commit()
    return note


@router.post(
    "/clinical-notes/{note_id}/finalize",
    response_model=ClinicalNoteRead,
    dependencies=[Depends(require_roles("practitioner", "medical_director"))],
)
async def finalize_clinical_note(
    note_id: uuid.UUID, user: AuthenticatedUser, session: DbSession
) -> ClinicalNoteRead:
    service = ClinicalNoteService(ClinicalNoteRepository(session))
    note = await service.finalize(note_id)
    await session.commit()
    return note
