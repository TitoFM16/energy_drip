import uuid
from datetime import datetime

from pydantic import BaseModel


class ClinicalNoteCreate(BaseModel):
    patient_id: uuid.UUID
    appointment_id: uuid.UUID | None = None
    content: str


class ClinicalNoteRead(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    author_user_id: uuid.UUID
    content: str
    is_finalized: bool
    finalized_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class MedicalHistoryEntryCreate(BaseModel):
    patient_id: uuid.UUID
    summary: str
    amends_entry_id: uuid.UUID | None = None


class MedicalHistoryEntryRead(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    author_user_id: uuid.UUID
    summary: str
    is_finalized: bool
    finalized_at: datetime | None
    amends_entry_id: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AllergyCreate(BaseModel):
    patient_id: uuid.UUID
    substance: str
    severity: str | None = None
    notes: str | None = None


class AllergyUpdate(BaseModel):
    substance: str | None = None
    severity: str | None = None
    notes: str | None = None
    is_active: bool | None = None


class AllergyRead(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    substance: str
    severity: str | None
    notes: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ConditionCreate(BaseModel):
    patient_id: uuid.UUID
    name: str
    diagnosed_on: datetime | None = None
    notes: str | None = None


class ConditionUpdate(BaseModel):
    name: str | None = None
    diagnosed_on: datetime | None = None
    notes: str | None = None
    is_active: bool | None = None


class ConditionRead(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    name: str
    diagnosed_on: datetime | None
    notes: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class MedicationCreate(BaseModel):
    patient_id: uuid.UUID
    name: str
    dosage: str | None = None


class MedicationUpdate(BaseModel):
    name: str | None = None
    dosage: str | None = None
    is_current: bool | None = None


class MedicationRead(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    name: str
    dosage: str | None
    is_current: bool
    created_at: datetime

    model_config = {"from_attributes": True}
