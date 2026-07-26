import asyncio
import uuid

import dramatiq
import structlog
from sqlalchemy import select

from medical_api.core.database import async_session_factory
from medical_api.modules.consents.models import ConsentTemplate, ConsentTemplateVersion
from medical_api.modules.consents.repository import ConsentRepository
from medical_api.modules.consents.service import ConsentService
from medical_api.modules.patients.repository import PatientRepository
from medical_worker import broker  # noqa: F401  (registers the Redis broker)
from medical_worker.activities.send_whatsapp import send_whatsapp_message

logger = structlog.get_logger(__name__)

CONSENT_WEB_BASE_URL = "https://consent.example.com/c"


@dramatiq.actor(max_retries=5, min_backoff=5_000, max_backoff=300_000)
def start_consent_request(organization_id: str, patient_id: str, appointment_id: str) -> None:
    asyncio.run(
        _start(uuid.UUID(organization_id), uuid.UUID(patient_id), uuid.UUID(appointment_id))
    )


async def _start(
    organization_id: uuid.UUID, patient_id: uuid.UUID, appointment_id: uuid.UUID
) -> None:
    async with async_session_factory() as session:
        stmt = (
            select(ConsentTemplateVersion.id)
            .join(ConsentTemplate, ConsentTemplate.id == ConsentTemplateVersion.template_id)
            .where(
                ConsentTemplate.organization_id == organization_id,
                ConsentTemplate.is_active.is_(True),
            )
            .order_by(ConsentTemplateVersion.version_number.desc())
            .limit(1)
        )
        template_version_id = (await session.execute(stmt)).scalar_one_or_none()
        if template_version_id is None:
            logger.warning(
                "consent_request.no_active_template", organization_id=str(organization_id)
            )
            return

        service = ConsentService(ConsentRepository(session), session)
        _, raw_token = await service.create_request(
            organization_id, patient_id, appointment_id, template_version_id
        )
        patient = await PatientRepository(session).get(organization_id, patient_id)
        await session.commit()

    if patient and patient.phone_number:
        link = f"{CONSENT_WEB_BASE_URL}/{raw_token}"
        send_whatsapp_message.send(patient.phone_number, "consent_link", [patient.first_name, link])
