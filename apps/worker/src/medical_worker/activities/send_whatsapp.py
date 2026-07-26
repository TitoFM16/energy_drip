import asyncio

import dramatiq
import structlog

from medical_api.integrations.whatsapp.client import WhatsAppClient
from medical_worker import broker  # noqa: F401  (registers the Redis broker)

logger = structlog.get_logger(__name__)


@dramatiq.actor(max_retries=5, min_backoff=5_000, max_backoff=300_000)
def send_whatsapp_message(to: str, template_name: str, params: list[str]) -> None:
    async def _send() -> None:
        client = WhatsAppClient()
        message_id = await client.send_template_message(to, template_name, params)
        logger.info("whatsapp.sent", to=to, template=template_name, provider_message_id=message_id)

    asyncio.run(_send())
