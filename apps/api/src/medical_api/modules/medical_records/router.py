import uuid

from fastapi import APIRouter, Depends

from medical_api.api.dependencies import AuthenticatedUser, DbSession
from medical_api.core.security import require_roles
from medical_api.modules.audit.service import AuditService
from medical_api.modules.medical_records.repository import (
    AllergyRepository,
    ClinicalNoteRepository,
    ConditionRepository,
    MedicalHistoryRepository,
    MedicationRepository,
)
from medical_api.modules.medical_records.schemas import (
    AllergyCreate,
    AllergyRead,
    AllergyUpdate,
    ClinicalNoteCreate,
    ClinicalNoteRead,
    ConditionCreate,
    ConditionRead,
    ConditionUpdate,
    MedicalHistoryEntryCreate,
    MedicalHistoryEntryRead,
    MedicationCreate,
    MedicationRead,
    MedicationUpdate,
)
from medical_api.modules.medical_records.service import (
    AllergyService,
    ClinicalNoteService,
    ConditionService,
    MedicalHistoryService,
    MedicationService,
)
from medical_api.modules.patients.repository import PatientRepository

router = APIRouter()

# Clinical content is restricted — reception/assistant roles can schedule
# around it but shouldn't read it (see "Authorization, audit, and security"
# in missing_features.md).
_CLINICAL_ROLES = ("organization_admin", "medical_director", "practitioner")
_CLINICAL_WRITE_ROLES = ("practitioner", "medical_director")


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


@router.get(
    "/{patient_id}/medical-history",
    response_model=list[MedicalHistoryEntryRead],
    dependencies=[Depends(require_roles(*_CLINICAL_ROLES))],
)
async def list_medical_history(
    patient_id: uuid.UUID, user: AuthenticatedUser, session: DbSession
) -> list[MedicalHistoryEntryRead]:
    service = MedicalHistoryService(MedicalHistoryRepository(session), PatientRepository(session))
    return await service.history(user.organization_id, patient_id)


@router.post(
    "/medical-history",
    response_model=MedicalHistoryEntryRead,
    status_code=201,
    dependencies=[Depends(require_roles(*_CLINICAL_WRITE_ROLES))],
)
async def create_medical_history_entry(
    payload: MedicalHistoryEntryCreate, user: AuthenticatedUser, session: DbSession
) -> MedicalHistoryEntryRead:
    service = MedicalHistoryService(MedicalHistoryRepository(session), PatientRepository(session))
    entry = await service.add_entry(user.organization_id, user.user_id, payload)
    await AuditService(session).record(
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        action="medical_history_entry.created",
        resource_type="patient_medical_history",
        resource_id=str(entry.id),
        metadata={"patient_id": str(entry.patient_id)},
    )
    await session.commit()
    return entry


@router.post(
    "/medical-history/{entry_id}/finalize",
    response_model=MedicalHistoryEntryRead,
    dependencies=[Depends(require_roles(*_CLINICAL_WRITE_ROLES))],
)
async def finalize_medical_history_entry(
    entry_id: uuid.UUID, user: AuthenticatedUser, session: DbSession
) -> MedicalHistoryEntryRead:
    service = MedicalHistoryService(MedicalHistoryRepository(session), PatientRepository(session))
    entry = await service.finalize(user.organization_id, entry_id)
    await AuditService(session).record(
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        action="medical_history_entry.finalized",
        resource_type="patient_medical_history",
        resource_id=str(entry.id),
    )
    await session.commit()
    return entry


@router.get(
    "/{patient_id}/allergies",
    response_model=list[AllergyRead],
    dependencies=[Depends(require_roles(*_CLINICAL_ROLES))],
)
async def list_allergies(
    patient_id: uuid.UUID, user: AuthenticatedUser, session: DbSession
) -> list[AllergyRead]:
    service = AllergyService(AllergyRepository(session), PatientRepository(session))
    return await service.list_for_patient(user.organization_id, patient_id)


@router.post(
    "/allergies",
    response_model=AllergyRead,
    status_code=201,
    dependencies=[Depends(require_roles(*_CLINICAL_WRITE_ROLES))],
)
async def create_allergy(
    payload: AllergyCreate, user: AuthenticatedUser, session: DbSession
) -> AllergyRead:
    service = AllergyService(AllergyRepository(session), PatientRepository(session))
    allergy = await service.create(user.organization_id, payload)
    await AuditService(session).record(
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        action="allergy.created",
        resource_type="patient_allergy",
        resource_id=str(allergy.id),
        metadata={"patient_id": str(allergy.patient_id)},
    )
    await session.commit()
    return allergy


@router.patch(
    "/allergies/{allergy_id}",
    response_model=AllergyRead,
    dependencies=[Depends(require_roles(*_CLINICAL_WRITE_ROLES))],
)
async def update_allergy(
    allergy_id: uuid.UUID, payload: AllergyUpdate, user: AuthenticatedUser, session: DbSession
) -> AllergyRead:
    service = AllergyService(AllergyRepository(session), PatientRepository(session))
    allergy = await service.update(user.organization_id, allergy_id, payload)
    await AuditService(session).record(
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        action="allergy.updated",
        resource_type="patient_allergy",
        resource_id=str(allergy.id),
        metadata={"fields": sorted(payload.model_dump(exclude_unset=True).keys())},
    )
    await session.commit()
    return allergy


@router.get(
    "/{patient_id}/conditions",
    response_model=list[ConditionRead],
    dependencies=[Depends(require_roles(*_CLINICAL_ROLES))],
)
async def list_conditions(
    patient_id: uuid.UUID, user: AuthenticatedUser, session: DbSession
) -> list[ConditionRead]:
    service = ConditionService(ConditionRepository(session), PatientRepository(session))
    return await service.list_for_patient(user.organization_id, patient_id)


@router.post(
    "/conditions",
    response_model=ConditionRead,
    status_code=201,
    dependencies=[Depends(require_roles(*_CLINICAL_WRITE_ROLES))],
)
async def create_condition(
    payload: ConditionCreate, user: AuthenticatedUser, session: DbSession
) -> ConditionRead:
    service = ConditionService(ConditionRepository(session), PatientRepository(session))
    condition = await service.create(user.organization_id, payload)
    await AuditService(session).record(
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        action="condition.created",
        resource_type="patient_condition",
        resource_id=str(condition.id),
        metadata={"patient_id": str(condition.patient_id)},
    )
    await session.commit()
    return condition


@router.patch(
    "/conditions/{condition_id}",
    response_model=ConditionRead,
    dependencies=[Depends(require_roles(*_CLINICAL_WRITE_ROLES))],
)
async def update_condition(
    condition_id: uuid.UUID, payload: ConditionUpdate, user: AuthenticatedUser, session: DbSession
) -> ConditionRead:
    service = ConditionService(ConditionRepository(session), PatientRepository(session))
    condition = await service.update(user.organization_id, condition_id, payload)
    await AuditService(session).record(
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        action="condition.updated",
        resource_type="patient_condition",
        resource_id=str(condition.id),
        metadata={"fields": sorted(payload.model_dump(exclude_unset=True).keys())},
    )
    await session.commit()
    return condition


@router.get(
    "/{patient_id}/medications",
    response_model=list[MedicationRead],
    dependencies=[Depends(require_roles(*_CLINICAL_ROLES))],
)
async def list_medications(
    patient_id: uuid.UUID, user: AuthenticatedUser, session: DbSession
) -> list[MedicationRead]:
    service = MedicationService(MedicationRepository(session), PatientRepository(session))
    return await service.list_for_patient(user.organization_id, patient_id)


@router.post(
    "/medications",
    response_model=MedicationRead,
    status_code=201,
    dependencies=[Depends(require_roles(*_CLINICAL_WRITE_ROLES))],
)
async def create_medication(
    payload: MedicationCreate, user: AuthenticatedUser, session: DbSession
) -> MedicationRead:
    service = MedicationService(MedicationRepository(session), PatientRepository(session))
    medication = await service.create(user.organization_id, payload)
    await AuditService(session).record(
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        action="medication.created",
        resource_type="patient_medication",
        resource_id=str(medication.id),
        metadata={"patient_id": str(medication.patient_id)},
    )
    await session.commit()
    return medication


@router.patch(
    "/medications/{medication_id}",
    response_model=MedicationRead,
    dependencies=[Depends(require_roles(*_CLINICAL_WRITE_ROLES))],
)
async def update_medication(
    medication_id: uuid.UUID,
    payload: MedicationUpdate,
    user: AuthenticatedUser,
    session: DbSession,
) -> MedicationRead:
    service = MedicationService(MedicationRepository(session), PatientRepository(session))
    medication = await service.update(user.organization_id, medication_id, payload)
    await AuditService(session).record(
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        action="medication.updated",
        resource_type="patient_medication",
        resource_id=str(medication.id),
        metadata={"fields": sorted(payload.model_dump(exclude_unset=True).keys())},
    )
    await session.commit()
    return medication
