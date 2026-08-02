import asyncio
from datetime import UTC, datetime

import dramatiq
import structlog
from sqlalchemy import select

from medical_api.core.database import async_session_factory
from medical_api.modules.notifications.models import NotificationMessage, NotificationStatus
from medical_worker import broker  # noqa: F401  (registers the Redis broker)

logger = structlog.get_logger(__name__)


@dramatiq.actor(max_retries=3)
def update_delivery_status(provider_message_id: str, status: str) -> None:
    """Applies a delivery-status webhook callback from the WhatsApp provider
    to the matching `NotificationMessage` row.
    """
    asyncio.run(_update(provider_message_id, NotificationStatus(status)))


async def _update(provider_message_id: str, status: NotificationStatus) -> None:
    async with async_session_factory() as session:
        stmt = select(NotificationMessage).where(
            NotificationMessage.provider_message_id == provider_message_id
        )
        message = (await session.execute(stmt)).scalar_one_or_none()
        if message is None:
            logger.warning(
                "notification.status_update.unmatched", provider_message_id=provider_message_id
            )
            return
        message.status = status
        if status == NotificationStatus.DELIVERED:
            message.delivered_at = datetime.now(UTC)
        await session.commit()
