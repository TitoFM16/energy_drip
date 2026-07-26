import uuid

from medical_api.core.exceptions import NotFoundError
from medical_api.modules.patients.models import Patient
from medical_api.modules.patients.repository import PatientRepository
from medical_api.modules.patients.schemas import PatientCreate, PatientUpdate


class PatientService:
    def __init__(self, repository: PatientRepository):
        self.repository = repository

    async def create(self, organization_id: uuid.UUID, data: PatientCreate) -> Patient:
        patient = Patient(organization_id=organization_id, **data.model_dump())
        return await self.repository.create(patient)

    async def get(self, organization_id: uuid.UUID, patient_id: uuid.UUID) -> Patient:
        patient = await self.repository.get(organization_id, patient_id)
        if patient is None:
            raise NotFoundError("Patient", patient_id)
        return patient

    async def search(self, organization_id: uuid.UUID, query: str | None) -> list[Patient]:
        return await self.repository.search(organization_id, query)

    async def update(
        self, organization_id: uuid.UUID, patient_id: uuid.UUID, data: PatientUpdate
    ) -> Patient:
        patient = await self.get(organization_id, patient_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(patient, field, value)
        await self.repository.create(patient)
        return patient
