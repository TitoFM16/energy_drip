from fastapi import APIRouter

from medical_api.modules.consents.router import public_router as consent_public_router

router = APIRouter()
router.include_router(consent_public_router, prefix="/consents", tags=["public-consents"])

__all__ = ["router"]
