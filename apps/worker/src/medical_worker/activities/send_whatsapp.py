import asyncio
import uuid
from datetime import UTC, datetime

import dramatiq
import structlog

from medical_api.integrations.whatsapp.client import (
    WhatsAppClient,
    WhatsAppNotConfiguredError,
    WhatsAppRejectedError,
)
from medical_api.modules.notifications.models import (
    NotificationCategory,
    NotificationMessage,
    NotificationStatus,
)
from medical_api.modules.patients.repository import PatientRepository
from medical_worker import broker  # noqa: F401  (registers the Redis broker)
from medical_worker.database import async_session_factory

logger = structlog.get_logger(__name__)


@dramatiq.actor(max_retries=5, min_backoff=5_000, max_backoff=300_000)
def send_whatsapp_message(
    to: str, template_name: str, params: list[str], notification_message_id: str | None = None
) -> None:
    """`notification_message_id` is the id of the `NotificationMessage` row
    the caller already created for this send — optional only so this actor
    doesn't hard-fail for a caller that hasn't been updated to pass one;
    without it, a delivery-status webhook callback has no
    `provider_message_id` to match back to a row (see webhook_router.py).
    """
    asyncio.run(_send(to, template_name, params, notification_message_id))


async def _send(
    to: str, template_name: str, params: list[str], notification_message_id: str | None
) -> None:
    if notification_message_id and await _suppress_opted_out_marketing(notification_message_id):
        return

    client = WhatsAppClient()
    try:
        message_id = await client.send_template_message(to, template_name, params)
    except (WhatsAppNotConfiguredError, WhatsAppRejectedError) as exc:
        # Permanent failure: every retry would produce the same outcome, so
        # log and stop here instead of letting dramatiq burn through
        # max_retries with growing backoff for nothing.
        # WhatsAppTransientError (rate limit / 5xx / network) is
        # deliberately NOT caught — it propagates so dramatiq's normal
        # retry policy applies, same as before this distinction existed.
        logger.error(
            "whatsapp.send_failed_permanently", to=to, template=template_name, error=str(exc)
        )
        if notification_message_id:
            await _mark_failed(notification_message_id, str(exc))
        return

    logger.info("whatsapp.sent", to=to, template=template_name, provider_message_id=message_id)
    if notification_message_id:
        await _mark_sent(notification_message_id, message_id)


async def _suppress_opted_out_marketing(notification_message_id: str) -> bool:
    """Return before provider delivery only for nonessential marketing.

    Appointment confirmations/reminders and consent links are categorized as
    transactional and intentionally bypass the marketing opt-out.
    """
    async with async_session_factory() as session:
        message = await session.get(NotificationMessage, uuid.UUID(notification_message_id))
        if message is None:
            logger.warning("whatsapp.notification_message_missing", id=notification_message_id)
            return False
        if message.category != NotificationCategory.MARKETING:
            return False

        patient = await PatientRepository(session).get_by_phone_number(
            message.organization_id, message.recipient
        )
        if patient is None or not patient.whatsapp_opt_out:
            return False

        message.status = NotificationStatus.SUPPRESSED
        await session.commit()
        logger.info(
            "whatsapp.marketing_suppressed",
            notification_message_id=notification_message_id,
            patient_id=str(patient.id),
        )
        return True


async def _mark_sent(notification_message_id: str, provider_message_id: str) -> None:
    async with async_session_factory() as session:
        message = await session.get(NotificationMessage, uuid.UUID(notification_message_id))
        if message is None:
            logger.warning("whatsapp.notification_message_missing", id=notification_message_id)
            return
        message.status = NotificationStatus.SENT
        message.provider_message_id = provider_message_id
        message.sent_at = datetime.now(UTC)
        await session.commit()


async def _mark_failed(notification_message_id: str, reason: str) -> None:
    async with async_session_factory() as session:
        message = await session.get(NotificationMessage, uuid.UUID(notification_message_id))
        if message is None:
            logger.warning("whatsapp.notification_message_missing", id=notification_message_id)
            return
        message.status = NotificationStatus.FAILED
        message.failure_reason = reason
        await session.commit()
