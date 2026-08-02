from fastapi import APIRouter

from medical_api.api.v1 import (
    appointments,
    auth,
    consents,
    notifications,
    patients,
    practitioners,
    public,
    treatments,
)
from medical_api.modules.audit.router import router as audit_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(patients.patients_router, prefix="/patients", tags=["patients"])
api_router.include_router(patients.clinical_router, prefix="/patients", tags=["clinical-records"])
api_router.include_router(appointments.router, prefix="/appointments", tags=["appointments"])
api_router.include_router(practitioners.router, prefix="/practitioners", tags=["practitioners"])
api_router.include_router(treatments.router, prefix="/treatments", tags=["treatments"])
api_router.include_router(consents.router, prefix="/consents", tags=["consents"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(audit_router, prefix="/audit", tags=["audit"])
api_router.include_router(public.router, prefix="/public", tags=["public"])
