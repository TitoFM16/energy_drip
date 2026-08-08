import asyncio
import uuid

import dramatiq
import structlog

from medical_api.modules.notifications.models import (
    NotificationCategory,
    NotificationChannel,
    NotificationMessage,
)
from medical_api.modules.patients.repository import PatientRepository
from medical_api.modules.scheduling.repository import AppointmentRepository
from medical_worker import broker  # noqa: F401  (registers the Redis broker)
from medical_worker.activities.send_whatsapp import send_whatsapp_message
from medical_worker.database import async_session_factory
from medical_worker.workflows.consent_request import start_consent_request

logger = structlog.get_logger(__name__)


@dramatiq.actor(max_retries=5, min_backoff=5_000, max_backoff=300_000)
def handle_appointment_scheduled(payload: dict) -> None:
    asyncio.run(_handle(uuid.UUID(payload["appointment_id"]), uuid.UUID(payload["patient_id"])))


async def _handle(appointment_id: uuid.UUID, patient_id: uuid.UUID) -> None:
    async with async_session_factory() as session:
        appointment = await AppointmentRepository(session).get_by_id(appointment_id)
        patient = await PatientRepository(session).get(appointment.organization_id, patient_id)
        if patient is None or not patient.phone_number:
            logger.warning("appointment_confirmation.no_phone", patient_id=str(patient_id))
            return

        message = NotificationMessage(
            organization_id=appointment.organization_id,
            channel=NotificationChannel.WHATSAPP,
            category=NotificationCategory.TRANSACTIONAL,
            recipient=patient.phone_number,
            template_key="appointment_confirmation",
            payload={"appointment_id": str(appointment_id)},
        )
        session.add(message)
        await session.commit()

    send_whatsapp_message.send(
        patient.phone_number,
        "appointment_confirmation",
        [patient.first_name, appointment.starts_at.isoformat()],
        str(message.id),
    )
    start_consent_request.send(
        str(appointment.organization_id), str(patient_id), str(appointment_id)
    )
