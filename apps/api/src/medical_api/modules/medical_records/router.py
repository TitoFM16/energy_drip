import uuid

from fastapi import APIRouter, Depends

from medical_api.api.dependencies import AuthenticatedUser, DbSession
from medical_api.core.security import require_roles
from medical_api.modules.audit.service import AuditService
from medical_api.modules.medical_records.repository import ClinicalNoteRepository
from medical_api.modules.medical_records.schemas import ClinicalNoteCreate, ClinicalNoteRead
from medical_api.modules.medical_records.service import ClinicalNoteService
from medical_api.modules.patients.repository import PatientRepository

router = APIRouter()

# Clinical note content is restricted clinical content — reception/assistant
# roles can schedule around it but shouldn't read it (see "Authorization,
# audit, and security" in missing_features.md).
_CLINICAL_ROLES = ("organization_admin", "medical_director", "practitioner")


@router.get(
    "/{patient_id}/clinical-notes",
    response_model=list[ClinicalNoteRead],
    dependencies=[Depends(require_roles(*_CLINICAL_ROLES))],
)
async def list_clinical_notes(
    patient_id: uuid.UUID, user: AuthenticatedUser, session: DbSession
) -> list[ClinicalNoteRead]:
    service = ClinicalNoteService(ClinicalNoteRepository(session), PatientRepository(session))
    return await service.history(user.organization_id, patient_id)


@router.post(
    "/clinical-notes",
    response_model=ClinicalNoteRead,
    status_code=201,
    dependencies=[Depends(require_roles("practitioner", "medical_director"))],
)
async def create_clinical_note(
    payload: ClinicalNoteCreate, user: AuthenticatedUser, session: DbSession
) -> ClinicalNoteRead:
    service = ClinicalNoteService(ClinicalNoteRepository(session), PatientRepository(session))
    note = await service.add_note(user.organization_id, user.user_id, payload)
    await AuditService(session).record(
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        action="clinical_note.created",
        resource_type="clinical_note",
        resource_id=str(note.id),
        metadata={"patient_id": str(note.patient_id)},
    )
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
    service = ClinicalNoteService(ClinicalNoteRepository(session), PatientRepository(session))
    note = await service.finalize(user.organization_id, note_id)
    await AuditService(session).record(
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        action="clinical_note.finalized",
        resource_type="clinical_note",
        resource_id=str(note.id),
    )
    await session.commit()
    return note
