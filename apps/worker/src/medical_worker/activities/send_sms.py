import asyncio

import dramatiq
import structlog

from medical_api.integrations.sms.client import SmsClient
from medical_worker import broker  # noqa: F401  (registers the Redis broker)

logger = structlog.get_logger(__name__)


@dramatiq.actor(max_retries=5, min_backoff=5_000, max_backoff=300_000)
def send_sms_message(to: str, body: str) -> None:
    async def _send() -> None:
        client = SmsClient()
        message_id = await client.send(to, body)
        logger.info("sms.sent", to=to, provider_message_id=message_id)

    asyncio.run(_send())
