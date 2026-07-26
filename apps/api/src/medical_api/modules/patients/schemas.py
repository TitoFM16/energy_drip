import uuid
from datetime import date

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

    model_config = {"from_attributes": True}
