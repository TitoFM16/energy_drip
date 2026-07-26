import uuid
from datetime import datetime

from pydantic import BaseModel, model_validator

from medical_api.modules.scheduling.models import AppointmentStatus


class AppointmentCreate(BaseModel):
    patient_id: uuid.UUID
    practitioner_id: uuid.UUID
    room_id: uuid.UUID | None = None
    treatment_definition_id: uuid.UUID | None = None
    starts_at: datetime
    ends_at: datetime
    notes: str | None = None

    @model_validator(mode="after")
    def check_time_range(self) -> "AppointmentCreate":
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        return self


class AppointmentStatusUpdate(BaseModel):
    status: AppointmentStatus
    reason: str | None = None


class AppointmentRead(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    patient_id: uuid.UUID
    practitioner_id: uuid.UUID
    room_id: uuid.UUID | None
    starts_at: datetime
    ends_at: datetime
    status: AppointmentStatus
    notes: str | None

    model_config = {"from_attributes": True}
