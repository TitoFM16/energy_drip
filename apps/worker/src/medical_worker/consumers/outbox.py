"""Polls `outbox_events` and dispatches each row to its dramatiq workflow
actor, then marks it processed. Runs as a standalone asyncio loop
(`python -m medical_worker.main`) separate from the dramatiq worker
processes that actually execute the enqueued actors.
"""

import asyncio
from datetime import UTC, datetime

import structlog
from sqlalchemy import func, select

from medical_api.core.database import async_session_factory
from medical_api.modules.notifications.models import OutboxEvent
from medical_worker.activities.update_delivery_status import update_delivery_status
from medical_worker.workflows.appointment_confirmation import handle_appointment_scheduled
from medical_worker.workflows.consent_document_generation import (
    handle_consent_submitted,
    handle_document_regenerate_requested,
)

logger = structlog.get_logger(__name__)

POLL_INTERVAL_SECONDS = 2
BATCH_SIZE = 50
MAX_ATTEMPTS = 5
# Purely a liveness/backlog signal for operators watching logs — at the
# default 2s poll interval this is roughly every 5 minutes. Without this,
# the only log line this loop ever produces is "started", so there's no
# way to distinguish "healthy and idle" from "silently stuck" without
# externally verifying a fresh outbox row actually gets processed.
HEARTBEAT_EVERY_N_POLLS = 150

_EVENT_HANDLERS = {
    "appointment.scheduled": handle_appointment_scheduled,
    "consent.submitted": handle_consent_submitted,
    "consent.document.regenerate_requested": handle_document_regenerate_requested,
    "whatsapp.delivery_status": update_delivery_status,
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


async def _backlog_size(session) -> int:
    stmt = select(func.count()).where(
        OutboxEvent.processed_at.is_(None), OutboxEvent.attempts < MAX_ATTEMPTS
    )
    return (await session.execute(stmt)).scalar_one()


async def run_outbox_consumer() -> None:
    logger.info("outbox_consumer.started", poll_interval=POLL_INTERVAL_SECONDS)
    polls = 0
    while True:
        await _process_once()
        polls += 1
        if polls % HEARTBEAT_EVERY_N_POLLS == 0:
            async with async_session_factory() as session:
                logger.info("outbox_consumer.heartbeat", backlog=await _backlog_size(session))
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
