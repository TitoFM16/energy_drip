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
