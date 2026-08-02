import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, DateTime, Identity, String, func
from sqlalchemy.orm import Mapped, mapped_column

from medical_api.core.database import Base, OrganizationScopedMixin, UUIDPrimaryKeyMixin


class AuditEvent(Base, UUIDPrimaryKeyMixin, OrganizationScopedMixin):
    __tablename__ = "audit_events"

    # `occurred_at` alone isn't a reliable ordering key: within a single DB
    # transaction, Postgres's now() is frozen to the transaction's start
    # time, so multiple events written in one transaction can share an
    # identical occurred_at. The hash chain's previous-event lookup (and
    # the listing route's ordering) need a strictly monotonic key instead —
    # `id` doesn't work either since it's a random UUID, not time-ordered.
    sequence: Mapped[int] = mapped_column(BigInteger, Identity(always=True), unique=True)
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
