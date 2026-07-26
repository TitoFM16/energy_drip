import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from medical_api.modules.notifications.models import OutboxEvent


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
