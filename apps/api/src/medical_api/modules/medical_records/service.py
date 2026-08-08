import uuid
from datetime import UTC, datetime

from medical_api.core.exceptions import ConflictError, NotFoundError
from medical_api.modules.medical_records.models import (
    ClinicalNote,
    PatientAllergy,
    PatientCondition,
    PatientMedicalHistory,
    PatientMedication,
)
from medical_api.modules.medical_records.repository import (
    AllergyRepository,
    ClinicalNoteRepository,
    ConditionRepository,
    MedicalHistoryRepository,
    MedicationRepository,
)
from medical_api.modules.medical_records.schemas import (
    AllergyCreate,
    AllergyUpdate,
    ClinicalNoteCreate,
    ConditionCreate,
    ConditionUpdate,
    MedicalHistoryEntryCreate,
    MedicationCreate,
    MedicationUpdate,
)
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


class MedicalHistoryService:
    def __init__(self, repository: MedicalHistoryRepository, patients: PatientRepository):
        self.repository = repository
        self.patients = patients

    async def add_entry(
        self, organization_id: uuid.UUID, author_user_id: uuid.UUID, data: MedicalHistoryEntryCreate
    ) -> PatientMedicalHistory:
        patient = await self.patients.get(organization_id, data.patient_id)
        if patient is None:
            raise NotFoundError("Patient", data.patient_id)
        if data.amends_entry_id is not None:
            amended = await self.repository.get(organization_id, data.amends_entry_id)
            if amended is None or amended.patient_id != data.patient_id:
                raise NotFoundError("PatientMedicalHistory", data.amends_entry_id)
        entry = PatientMedicalHistory(author_user_id=author_user_id, **data.model_dump())
        return await self.repository.create(entry)

    async def finalize(
        self, organization_id: uuid.UUID, entry_id: uuid.UUID
    ) -> PatientMedicalHistory:
        entry = await self.repository.get(organization_id, entry_id)
        if entry is None:
            raise NotFoundError("PatientMedicalHistory", entry_id)
        if entry.is_finalized:
            raise ConflictError(f"Medical history entry {entry_id} is already finalized")
        entry.is_finalized = True
        entry.finalized_at = datetime.now(UTC)
        return entry

    async def history(
        self, organization_id: uuid.UUID, patient_id: uuid.UUID
    ) -> list[PatientMedicalHistory]:
        return await self.repository.list_for_patient(organization_id, patient_id)


class AllergyService:
    def __init__(self, repository: AllergyRepository, patients: PatientRepository):
        self.repository = repository
        self.patients = patients

    async def create(self, organization_id: uuid.UUID, data: AllergyCreate) -> PatientAllergy:
        patient = await self.patients.get(organization_id, data.patient_id)
        if patient is None:
            raise NotFoundError("Patient", data.patient_id)
        allergy = PatientAllergy(**data.model_dump())
        return await self.repository.create(allergy)

    async def list_for_patient(
        self, organization_id: uuid.UUID, patient_id: uuid.UUID
    ) -> list[PatientAllergy]:
        return await self.repository.list_for_patient(organization_id, patient_id)

    async def update(
        self, organization_id: uuid.UUID, allergy_id: uuid.UUID, data: AllergyUpdate
    ) -> PatientAllergy:
        allergy = await self.repository.get(organization_id, allergy_id)
        if allergy is None:
            raise NotFoundError("PatientAllergy", allergy_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(allergy, field, value)
        return allergy


class ConditionService:
    def __init__(self, repository: ConditionRepository, patients: PatientRepository):
        self.repository = repository
        self.patients = patients

    async def create(self, organization_id: uuid.UUID, data: ConditionCreate) -> PatientCondition:
        patient = await self.patients.get(organization_id, data.patient_id)
        if patient is None:
            raise NotFoundError("Patient", data.patient_id)
        condition = PatientCondition(**data.model_dump())
        return await self.repository.create(condition)

    async def list_for_patient(
        self, organization_id: uuid.UUID, patient_id: uuid.UUID
    ) -> list[PatientCondition]:
        return await self.repository.list_for_patient(organization_id, patient_id)

    async def update(
        self, organization_id: uuid.UUID, condition_id: uuid.UUID, data: ConditionUpdate
    ) -> PatientCondition:
        condition = await self.repository.get(organization_id, condition_id)
        if condition is None:
            raise NotFoundError("PatientCondition", condition_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(condition, field, value)
        return condition


class MedicationService:
    def __init__(self, repository: MedicationRepository, patients: PatientRepository):
        self.repository = repository
        self.patients = patients

    async def create(self, organization_id: uuid.UUID, data: MedicationCreate) -> PatientMedication:
        patient = await self.patients.get(organization_id, data.patient_id)
        if patient is None:
            raise NotFoundError("Patient", data.patient_id)
        medication = PatientMedication(**data.model_dump())
        return await self.repository.create(medication)

    async def list_for_patient(
        self, organization_id: uuid.UUID, patient_id: uuid.UUID
    ) -> list[PatientMedication]:
        return await self.repository.list_for_patient(organization_id, patient_id)

    async def update(
        self, organization_id: uuid.UUID, medication_id: uuid.UUID, data: MedicationUpdate
    ) -> PatientMedication:
        medication = await self.repository.get(organization_id, medication_id)
        if medication is None:
            raise NotFoundError("PatientMedication", medication_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(medication, field, value)
        return medication
