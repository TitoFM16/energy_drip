import asyncio
from datetime import UTC, datetime

import dramatiq
import structlog
from sqlalchemy import select

from medical_api.modules.notifications.models import NotificationMessage, NotificationStatus
from medical_worker import broker  # noqa: F401  (registers the Redis broker)
from medical_worker.database import async_session_factory

logger = structlog.get_logger(__name__)

# Monotonic-enough ordering to reject a stale/out-of-order callback rather
# than regress an already-more-advanced status. FAILED is deliberately not
# ranked here — see _should_apply.
_STATUS_RANK = {
    NotificationStatus.PENDING: 0,
    NotificationStatus.SENT: 1,
    NotificationStatus.DELIVERED: 2,
}


def _should_apply(current: NotificationStatus, incoming: NotificationStatus) -> bool:
    if incoming == NotificationStatus.FAILED:
        # A late "failed" for a message we've already confirmed delivered
        # is almost certainly a stale/out-of-order callback, not a real
        # regression — Meta doesn't fail a message after delivering it.
        return current != NotificationStatus.DELIVERED
    if current == NotificationStatus.FAILED:
        # Once failed, only a later terminal-ish update should move it —
        # in practice this doesn't happen, but don't let a reordered
        # "sent" from before the failure quietly erase it.
        return False
    return _STATUS_RANK.get(incoming, 0) >= _STATUS_RANK.get(current, 0)


@dramatiq.actor(max_retries=3)
def update_delivery_status(payload: dict) -> None:
    """Applies one delivery-status webhook callback from the WhatsApp
    provider to the matching `NotificationMessage` row. `payload` matches
    `medical_api.integrations.whatsapp.webhook.StatusUpdate`: one row per
    provider message id, dispatched via the transactional outbox (event
    type `whatsapp.delivery_status`) rather than called directly.
    """
    asyncio.run(
        _update(
            payload["provider_message_id"],
            NotificationStatus(payload["status"]),
            payload.get("failure_reason"),
        )
    )


async def _update(
    provider_message_id: str, status: NotificationStatus, failure_reason: str | None
) -> None:
    async with async_session_factory() as session:
        stmt = select(NotificationMessage).where(
            NotificationMessage.provider_message_id == provider_message_id
        )
        message = (await session.execute(stmt)).scalar_one_or_none()
        if message is None:
            # Expected in dev (no real provider_message_id is ever set
            # without live Meta credentials) and also a legitimate race in
            # production: a delivery callback can arrive before the send
            # actor has finished writing provider_message_id back onto the
            # row. Not retried — a real duplicate/retry from Meta will
            # arrive again and find the row by then.
            logger.warning(
                "notification.status_update.unmatched", provider_message_id=provider_message_id
            )
            return

        if not _should_apply(message.status, status):
            logger.info(
                "notification.status_update.ignored_out_of_order",
                provider_message_id=provider_message_id,
                current=message.status,
                incoming=status,
            )
            return

        message.status = status
        if status == NotificationStatus.DELIVERED:
            message.delivered_at = datetime.now(UTC)
        if status == NotificationStatus.FAILED:
            message.failure_reason = failure_reason
        await session.commit()
