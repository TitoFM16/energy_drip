"""Polls `outbox_events` and dispatches each row to its dramatiq workflow
actor, then marks it processed. Runs as a standalone asyncio loop
(`python -m medical_worker.main`) separate from the dramatiq worker
processes that actually execute the enqueued actors.
"""

import asyncio
from datetime import UTC, datetime

import structlog
from sqlalchemy import select

from medical_api.core.database import async_session_factory
from medical_api.modules.notifications.models import OutboxEvent
from medical_worker.workflows.appointment_confirmation import handle_appointment_scheduled
from medical_worker.workflows.consent_document_generation import handle_consent_submitted

logger = structlog.get_logger(__name__)

POLL_INTERVAL_SECONDS = 2
BATCH_SIZE = 50
MAX_ATTEMPTS = 5

_EVENT_HANDLERS = {
    "appointment.scheduled": handle_appointment_scheduled,
    "consent.submitted": handle_consent_submitted,
}


async def _fetch_unprocessed(session) -> list[OutboxEvent]:
    stmt = (
        select(OutboxEvent)
        .where(OutboxEvent.processed_at.is_(None), OutboxEvent.attempts < MAX_ATTEMPTS)
        .order_by(OutboxEvent.occurred_at)
        .limit(BATCH_SIZE)
        .with_for_update(skip_locked=True)
    )
    return list((await session.execute(stmt)).scalars().all())


async def _process_once() -> None:
    async with async_session_factory() as session:
        events = await _fetch_unprocessed(session)
        for event in events:
            handler = _EVENT_HANDLERS.get(event.event_type)
            event.attempts += 1
            try:
                if handler is None:
                    logger.warning("outbox.unknown_event_type", event_type=event.event_type)
                else:
                    handler.send(event.payload)
                event.processed_at = datetime.now(UTC)
            except Exception as exc:
                event.last_error = str(exc)
                logger.error("outbox.dispatch_failed", event_id=str(event.id), error=str(exc))
        await session.commit()


async def run_outbox_consumer() -> None:
    logger.info("outbox_consumer.started", poll_interval=POLL_INTERVAL_SECONDS)
    while True:
        await _process_once()
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
