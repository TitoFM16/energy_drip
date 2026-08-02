from fastapi import APIRouter

from medical_api.api.v1.booking import booking_public_router
from medical_api.modules.consents.router import public_router as consent_public_router

router = APIRouter()
router.include_router(consent_public_router, prefix="/consents", tags=["public-consents"])
router.include_router(booking_public_router, prefix="", tags=["public-booking"])

__all__ = ["router"]
