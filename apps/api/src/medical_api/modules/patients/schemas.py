import uuid
from datetime import date, datetime

from pydantic import BaseModel, EmailStr


class PatientCreate(BaseModel):
    first_name: str
    last_name: str
    document_id: str | None = None
    date_of_birth: date | None = None
    phone_number: str | None = None
    email: EmailStr | None = None


class PatientUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    document_id: str | None = None
    date_of_birth: date | None = None
    phone_number: str | None = None
    email: EmailStr | None = None
    is_active: bool | None = None


class PatientRead(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    first_name: str
    last_name: str
    document_id: str | None
    date_of_birth: date | None
    phone_number: str | None
    email: str | None
    is_active: bool
    whatsapp_opt_out: bool
    whatsapp_opt_out_at: datetime | None
    whatsapp_opt_in_at: datetime | None

    model_config = {"from_attributes": True}


class PatientCommunicationPreferencesUpdate(BaseModel):
    whatsapp_opt_out: bool


class PatientCommunicationPreferencesRead(BaseModel):
    patient_id: uuid.UUID
    phone_number: str | None
    whatsapp_opt_out: bool
    whatsapp_opt_out_at: datetime | None
    whatsapp_opt_in_at: datetime | None


class PatientContactCreate(BaseModel):
    patient_id: uuid.UUID
    label: str
    phone_number: str | None = None
    email: EmailStr | None = None


class PatientContactUpdate(BaseModel):
    label: str | None = None
    phone_number: str | None = None
    email: EmailStr | None = None


class PatientContactRead(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    label: str
    phone_number: str | None
    email: str | None

    model_config = {"from_attributes": True}


class EmergencyContactCreate(BaseModel):
    patient_id: uuid.UUID
    full_name: str
    relationship: str | None = None
    phone_number: str


class EmergencyContactUpdate(BaseModel):
    full_name: str | None = None
    relationship: str | None = None
    phone_number: str | None = None


class EmergencyContactRead(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    full_name: str
    relationship: str | None
    phone_number: str

    model_config = {"from_attributes": True}
