import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from medical_api.core.exceptions import ConflictError, NotFoundError
from medical_api.modules.notifications.models import (
    NotificationMessage,
    NotificationStatus,
    OutboxEvent,
)

# The only template whose send params (patient first name + appointment
# time) are cheap to re-derive from current DB state — a blind retry is
# safe. consent_link's original link embedded a single-use token that was
# never persisted (deliberately — see ConsentRequest's docstring), so
# retrying it for real means creating a new request via the existing
# resend_request flow (modules/consents/service.py), not resending the old,
# now-orphaned link.
_RETRYABLE_TEMPLATE_KEYS = {"appointment_confirmation"}


async def enqueue_event(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    event_type: str,
    payload: dict[str, Any],
) -> OutboxEvent:
    """Writes a domain event to the outbox within the caller's transaction.

    Callers must commit alongside their own domain change so the write and
    the event are atomic; the worker polls `outbox_events` separately.
    """
    event = OutboxEvent(organization_id=organization_id, event_type=event_type, payload=payload)
    session.add(event)
    await session.flush()
    return event


class NotificationService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def retry(self, organization_id: uuid.UUID, message_id: uuid.UUID) -> NotificationMessage:
        message = await self.session.get(NotificationMessage, message_id)
        if message is None or message.organization_id != organization_id:
            raise NotFoundError("NotificationMessage", message_id)
        if message.status != NotificationStatus.FAILED:
            raise ConflictError(
                f"Only a failed notification can be retried (current status: {message.status})"
            )
        if message.template_key not in _RETRYABLE_TEMPLATE_KEYS:
            raise ConflictError(
                f"'{message.template_key}' notifications can't be retried automatically. "
                "For a consent link, resend the consent request instead."
            )

        message.status = NotificationStatus.PENDING
        message.failure_reason = None
        await self.session.flush()
        # Same write-then-async-consume split as every other workflow here:
        # the worker's outbox consumer re-derives fresh send params and
        # dispatches the actual WhatsApp send.
        await enqueue_event(
            self.session,
            organization_id=organization_id,
            event_type="notification.retry_requested",
            payload={"notification_message_id": str(message.id)},
        )
        return message
