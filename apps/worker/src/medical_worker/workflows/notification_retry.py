"""Re-sends a notification the API marked back to PENDING via
NotificationService.retry — only ever enqueued for template keys that
service considers safely blind-retryable (see its _RETRYABLE_TEMPLATE_KEYS).
Re-derives send params from current DB state rather than trusting anything
persisted from the original attempt, since NotificationMessage.payload only
ever stored IDs, not the resolved template params themselves.
"""

import asyncio
import uuid

import dramatiq
import structlog

from medical_api.modules.notifications.models import NotificationMessage
from medical_api.modules.patients.repository import PatientRepository
from medical_api.modules.scheduling.repository import AppointmentRepository
from medical_worker import broker  # noqa: F401  (registers the Redis broker)
from medical_worker.activities.send_whatsapp import send_whatsapp_message
from medical_worker.database import async_session_factory

logger = structlog.get_logger(__name__)


@dramatiq.actor(max_retries=5, min_backoff=5_000, max_backoff=300_000)
def handle_notification_retry_requested(payload: dict) -> None:
    asyncio.run(_handle(uuid.UUID(payload["notification_message_id"])))


async def _handle(notification_message_id: uuid.UUID) -> None:
    async with async_session_factory() as session:
        message = await session.get(NotificationMessage, notification_message_id)
        if message is None:
            logger.warning("notification_retry.message_missing", id=str(notification_message_id))
            return

        if message.template_key != "appointment_confirmation":
            # Defensive only — the API already rejects any other
            # template_key before this event is ever enqueued.
            logger.error(
                "notification_retry.unsupported_template_key",
                id=str(notification_message_id),
                template_key=message.template_key,
            )
            return

        appointment_id = uuid.UUID(message.payload["appointment_id"])
        appointment = await AppointmentRepository(session).get_by_id(appointment_id)
        if appointment is None:
            logger.warning(
                "notification_retry.appointment_missing", appointment_id=str(appointment_id)
            )
            return
        patient = await PatientRepository(session).get(
            appointment.organization_id, appointment.patient_id
        )
        if patient is None or not patient.phone_number:
            logger.warning("notification_retry.no_phone", patient_id=str(appointment.patient_id))
            return

    send_whatsapp_message.send(
        patient.phone_number,
        "appointment_confirmation",
        [patient.first_name, appointment.starts_at.isoformat()],
        str(notification_message_id),
    )
