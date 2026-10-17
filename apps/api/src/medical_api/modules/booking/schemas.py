import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import AwareDatetime, BaseModel, EmailStr, Field

from medical_api.modules.booking.models import BookingRequestStatus


class PublicTreatmentRead(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    price: Decimal
    currency: str
    duration_minutes: int
    image_url: str | None

    model_config = {"from_attributes": True}


class BookingRequestCreate(BaseModel):
    treatment_definition_id: uuid.UUID
    first_name: str = Field(min_length=1, max_length=150)
    last_name: str = Field(min_length=1, max_length=150)
    phone_number: str = Field(min_length=5, max_length=30)
    email: EmailStr | None = None
    preferred_date: date | None = None
    message: str | None = Field(default=None, max_length=2000)
    # Honeypot: styled off-screen in the real form, so a human never sees
    # or fills it. Any non-empty value marks the submission as automated;
    # the response looks identical either way so a bot can't learn it was
    # filtered (see BookingRequestService.create_request).
    website: str = ""


class BookingRequestConfirmation(BaseModel):
    detail: str


class BookingRequestRead(BaseModel):
    id: uuid.UUID
    treatment_definition_id: uuid.UUID
    first_name: str
    last_name: str
    phone_number: str
    email: str | None
    preferred_date: date | None
    message: str | None
    status: BookingRequestStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class BookingRequestStatusUpdate(BaseModel):
    status: BookingRequestStatus


class PublicPractitionerRead(BaseModel):
    id: uuid.UUID
    full_name: str
    specialty: str | None


class PublicAppointmentCreate(BaseModel):
    treatment_definition_id: uuid.UUID
    practitioner_id: uuid.UUID
    starts_at: AwareDatetime
    first_name: str = Field(min_length=1, max_length=150)
    last_name: str = Field(min_length=1, max_length=150)
    phone_number: str = Field(min_length=5, max_length=30, pattern=r"^[+0-9() .-]+$")
    email: EmailStr | None = None
    message: str | None = Field(default=None, max_length=2000)
    website: str = Field(default="", max_length=2000)

    model_config = {"str_strip_whitespace": True}


class PublicAppointmentConfirmation(BaseModel):
    id: uuid.UUID
    starts_at: datetime
    ends_at: datetime
    status: str
    treatment_name: str
    practitioner_name: str
    detail: str
