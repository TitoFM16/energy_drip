import uuid
from datetime import datetime, time

from pydantic import BaseModel, Field, model_validator

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


class AppointmentReschedule(BaseModel):
    starts_at: datetime
    ends_at: datetime

    @model_validator(mode="after")
    def check_time_range(self) -> "AppointmentReschedule":
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        return self


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


class AppointmentStatusHistoryRead(BaseModel):
    id: uuid.UUID
    from_status: AppointmentStatus | None
    to_status: AppointmentStatus
    changed_by_user_id: uuid.UUID | None
    changed_by_full_name: str | None
    changed_at: datetime
    reason: str | None


class AvailabilityRuleCreate(BaseModel):
    practitioner_id: uuid.UUID
    weekday: int = Field(ge=0, le=6, description="0 = Monday ... 6 = Sunday")
    start_time: time
    end_time: time

    @model_validator(mode="after")
    def check_time_range(self) -> "AvailabilityRuleCreate":
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


class AvailabilityRuleRead(BaseModel):
    id: uuid.UUID
    practitioner_id: uuid.UUID
    weekday: int
    start_time: time
    end_time: time

    model_config = {"from_attributes": True}


class AvailableSlot(BaseModel):
    starts_at: datetime
    ends_at: datetime


class PractitionerCreate(BaseModel):
    user_id: uuid.UUID
    specialty: str | None = None


class PractitionerUpdate(BaseModel):
    specialty: str | None = None
    is_active: bool | None = None


class PractitionerRead(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    user_id: uuid.UUID
    specialty: str | None
    is_active: bool
    full_name: str
    email: str

    model_config = {"from_attributes": True}
