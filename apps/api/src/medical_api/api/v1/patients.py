from medical_api.modules.medical_records.router import router as clinical_router
from medical_api.modules.patients.router import router as patients_router

__all__ = ["clinical_router", "patients_router"]
