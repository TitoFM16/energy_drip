import uuid
from datetime import datetime
from decimal import Decimal
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator, model_validator

from medical_api.modules.treatments.models import TreatmentPlanStatus


class ServiceImageFields(BaseModel):
    image_url: str | None = Field(default=None, max_length=2048)

    @field_validator("image_url")
    @classmethod
    def validate_image_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if value.startswith("/media/services/") and ".." not in value and "\\" not in value:
            return value
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Use an http(s) image URL or an uploaded service image")
        return value


class TreatmentDefinitionCreate(ServiceImageFields):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=5000)
    default_session_count: int = Field(default=1, ge=1)
    price: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)
    currency: str = Field(default="COP", pattern=r"^[A-Z]{3}$")
    duration_minutes: int = Field(default=60, ge=5, le=480)
    is_active: bool = True

    model_config = {"str_strip_whitespace": True}


class TreatmentDefinitionUpdate(ServiceImageFields):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=5000)
    default_session_count: int | None = Field(default=None, ge=1)
    price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    duration_minutes: int | None = Field(default=None, ge=5, le=480)
    is_active: bool | None = None

    model_config = {"str_strip_whitespace": True}

    @model_validator(mode="after")
    def reject_null_required_fields(self) -> "TreatmentDefinitionUpdate":
        for field in self.model_fields_set - {"description", "image_url"}:
            if getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class TreatmentDefinitionRead(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    default_session_count: int
    price: Decimal
    currency: str
    duration_minutes: int
    image_url: str | None
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
    is_finalized: bool
    finalized_at: datetime | None

    model_config = {"from_attributes": True}
