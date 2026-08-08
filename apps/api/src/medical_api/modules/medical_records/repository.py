import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import ColumnElement

from medical_api.modules.medical_records.models import (
    ClinicalNote,
    PatientAllergy,
    PatientCondition,
    PatientMedicalHistory,
    PatientMedication,
)
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


class _PatientScopedRepository[
    ModelT: (PatientMedicalHistory, PatientAllergy, PatientCondition, PatientMedication)
]:
    """Shared join-through-Patient pattern: none of these models carry their
    own organization_id (same reasoning as ClinicalNote — see
    ClinicalNoteRepository above and the "Complete server-side authorization
    review" section of missing_features.md), so every query has to join
    Patient to check organization_id.
    """

    model: type[ModelT]
    order_by: ColumnElement[object]

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
            .order_by(self.order_by)
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


class MedicalHistoryRepository(_PatientScopedRepository[PatientMedicalHistory]):
    model = PatientMedicalHistory
    order_by = PatientMedicalHistory.created_at.desc()


class AllergyRepository(_PatientScopedRepository[PatientAllergy]):
    model = PatientAllergy
    order_by = PatientAllergy.created_at.desc()


class ConditionRepository(_PatientScopedRepository[PatientCondition]):
    model = PatientCondition
    order_by = PatientCondition.created_at.desc()


class MedicationRepository(_PatientScopedRepository[PatientMedication]):
    model = PatientMedication
    order_by = PatientMedication.created_at.desc()
