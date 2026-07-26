import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from medical_api.core.database import Base, OrganizationScopedMixin, UUIDPrimaryKeyMixin


class AuditEvent(Base, UUIDPrimaryKeyMixin, OrganizationScopedMixin):
    __tablename__ = "audit_events"

    actor_user_id: Mapped[uuid.UUID | None]
    action: Mapped[str] = mapped_column(String(100), index=True)
    resource_type: Mapped[str] = mapped_column(String(100))
    resource_id: Mapped[str]
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    request_id: Mapped[str | None]
    ip_address: Mapped[str | None]
    user_agent: Mapped[str | None]
    previous_hash: Mapped[str | None]
    event_hash: Mapped[str]
    event_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
