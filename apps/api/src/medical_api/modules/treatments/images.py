"""Admin service-image uploads. Only decoded raster pixels are published."""

import io
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError
from starlette.concurrency import run_in_threadpool

from medical_api.api.dependencies import AuthenticatedUser, DbSession
from medical_api.core.config import get_settings
from medical_api.core.exceptions import NotFoundError
from medical_api.core.security import require_roles
from medical_api.modules.audit.service import AuditService
from medical_api.modules.treatments.repository import TreatmentDefinitionRepository
from medical_api.modules.treatments.schemas import TreatmentDefinitionRead

router = APIRouter()
MAX_IMAGE_BYTES = 5 * 1024 * 1024


def store_service_image(data: bytes) -> str:
    try:
        with Image.open(io.BytesIO(data)) as original:
            if original.format not in {"JPEG", "PNG", "WEBP"}:
                raise ValueError("Use una imagen JPG, PNG o WebP")
            if original.width * original.height > 20_000_000:
                raise ValueError("La imagen supera 20 megapíxeles")
            original.load()
            image = original.convert("RGB")
            image.thumbnail((1600, 1600))
            filename = f"{uuid.uuid4()}.webp"
            directory = get_settings().public_media_path / "services"
            directory.mkdir(parents=True, exist_ok=True)
            image.save(directory / filename, format="WEBP", quality=85)
            return f"/media/services/{filename}"
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValueError("El archivo no es una imagen válida") from exc


@router.post(
    "/definitions/{definition_id}/image",
    response_model=TreatmentDefinitionRead,
    dependencies=[Depends(require_roles("organization_admin", "medical_director"))],
)
async def upload_service_image(
    definition_id: uuid.UUID,
    file: UploadFile,
    user: AuthenticatedUser,
    session: DbSession,
) -> TreatmentDefinitionRead:
    definition = await TreatmentDefinitionRepository(session).get(
        user.organization_id, definition_id
    )
    if definition is None:
        raise NotFoundError("TreatmentDefinition", definition_id)
    data = await file.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(413, "La imagen debe pesar menos de 5 MB")
    try:
        definition.image_url = await run_in_threadpool(store_service_image, data)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    await AuditService(session).record(
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        action="treatment_definition.image_updated",
        resource_type="treatment_definition",
        resource_id=str(definition.id),
    )
    await session.commit()
    return definition
