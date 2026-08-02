import asyncio

import dramatiq
import structlog

from medical_api.integrations.whatsapp.client import (
    WhatsAppClient,
    WhatsAppNotConfiguredError,
    WhatsAppRejectedError,
)
from medical_worker import broker  # noqa: F401  (registers the Redis broker)

logger = structlog.get_logger(__name__)


@dramatiq.actor(max_retries=5, min_backoff=5_000, max_backoff=300_000)
def send_whatsapp_message(to: str, template_name: str, params: list[str]) -> None:
    asyncio.run(_send(to, template_name, params))


async def _send(to: str, template_name: str, params: list[str]) -> None:
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
        return
    logger.info("whatsapp.sent", to=to, template=template_name, provider_message_id=message_id)
