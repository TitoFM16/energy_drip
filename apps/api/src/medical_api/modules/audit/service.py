import hashlib
import json
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from medical_api.modules.audit.models import AuditEvent


class AuditService:
    """Append-only audit trail with hash chaining per organization.

    Each event's hash covers the previous event's hash so the chain can be
    verified end-to-end; entries are never updated or deleted.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def _last_hash(self, organization_id: uuid.UUID) -> str | None:
        stmt = (
            select(AuditEvent.event_hash)
            .where(AuditEvent.organization_id == organization_id)
            .order_by(AuditEvent.occurred_at.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def record(
        self,
        *,
        organization_id: uuid.UUID,
        actor_user_id: uuid.UUID | None,
        action: str,
        resource_type: str,
        resource_id: str,
        request_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditEvent:
        previous_hash = await self._last_hash(organization_id)
        payload = {
            "organization_id": str(organization_id),
            "actor_user_id": str(actor_user_id) if actor_user_id else None,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "previous_hash": previous_hash,
            "metadata": metadata or {},
        }
        event_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        event = AuditEvent(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            request_id=request_id,
            ip_address=ip_address,
            user_agent=user_agent,
            previous_hash=previous_hash,
            event_hash=event_hash,
            event_metadata=metadata or {},
        )
        self.session.add(event)
        await self.session.flush()
        return event
