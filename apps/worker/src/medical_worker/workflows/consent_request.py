import asyncio
import uuid

import dramatiq
import structlog
from sqlalchemy import select

from medical_api.core.config import get_settings
from medical_api.modules.consents.models import ConsentTemplate, ConsentTemplateVersion
from medical_api.modules.consents.repository import ConsentRepository
from medical_api.modules.consents.service import ConsentService
from medical_api.modules.notifications.models import (
    NotificationCategory,
    NotificationChannel,
    NotificationMessage,
)
from medical_api.modules.patients.repository import PatientRepository
from medical_worker import broker  # noqa: F401  (registers the Redis broker)
from medical_worker.activities.send_whatsapp import send_whatsapp_message
from medical_worker.database import async_session_factory

logger = structlog.get_logger(__name__)

settings = get_settings()


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
        if patient is None or not patient.phone_number:
            await session.commit()
            return

        link = f"{settings.patient_web_base_url}/c/{raw_token}"
        message = NotificationMessage(
            organization_id=organization_id,
            channel=NotificationChannel.WHATSAPP,
            category=NotificationCategory.TRANSACTIONAL,
            recipient=patient.phone_number,
            template_key="consent_link",
            payload={"appointment_id": str(appointment_id), "patient_id": str(patient_id)},
        )
        session.add(message)
        await session.commit()

    send_whatsapp_message.send(
        patient.phone_number, "consent_link", [patient.first_name, link], str(message.id)
    )
