import uuid
from datetime import datetime

from pydantic import BaseModel

from medical_api.modules.treatments.models import TreatmentPlanStatus


class TreatmentDefinitionCreate(BaseModel):
    name: str
    description: str | None = None
    default_session_count: int = 1


class TreatmentDefinitionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    default_session_count: int | None = None
    is_active: bool | None = None


class TreatmentDefinitionRead(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    default_session_count: int
    is_active: bool

    model_config = {"from_attributes": True}


class TreatmentPlanCreate(BaseModel):
    patient_id: uuid.UUID
    treatment_definition_id: uuid.UUID
    planned_session_count: int
    notes: str | None = None


class TreatmentPlanUpdate(BaseModel):
    status: TreatmentPlanStatus | None = None
    notes: str | None = None


class TreatmentPlanRead(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    treatment_definition_id: uuid.UUID
    status: TreatmentPlanStatus
    planned_session_count: int
    notes: str | None

    model_config = {"from_attributes": True}


class TreatmentSessionCreate(BaseModel):
    treatment_plan_id: uuid.UUID
    practitioner_id: uuid.UUID
    session_number: int
    appointment_id: uuid.UUID | None = None
    clinical_evolution: str | None = None


class TreatmentSessionRead(BaseModel):
    id: uuid.UUID
    treatment_plan_id: uuid.UUID
    practitioner_id: uuid.UUID
    session_number: int
    performed_at: datetime | None
    clinical_evolution: str | None

    model_config = {"from_attributes": True}
