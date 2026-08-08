import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from medical_api.core.database import (
    Base,
    OrganizationScopedMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class NotificationChannel(StrEnum):
    WHATSAPP = "whatsapp"
    SMS = "sms"
    EMAIL = "email"


class NotificationStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    SUPPRESSED = "suppressed"


class NotificationCategory(StrEnum):
    TRANSACTIONAL = "transactional"
    MARKETING = "marketing"


class OutboxEvent(Base, UUIDPrimaryKeyMixin, OrganizationScopedMixin):
    """Transactional outbox: written in the same DB transaction as the domain
    change, then polled and dispatched by the worker. Guarantees at-least-once
    delivery without a synchronous call to an external provider.
    """

    __tablename__ = "outbox_events"

    event_type: Mapped[str] = mapped_column(String(100), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(default=0)
    last_error: Mapped[str | None]


class NotificationMessage(Base, UUIDPrimaryKeyMixin, TimestampMixin, OrganizationScopedMixin):
    __tablename__ = "notification_messages"

    channel: Mapped[NotificationChannel]
    category: Mapped[NotificationCategory] = mapped_column(
        default=NotificationCategory.TRANSACTIONAL
    )
    status: Mapped[NotificationStatus] = mapped_column(default=NotificationStatus.PENDING)
    recipient: Mapped[str]
    template_key: Mapped[str] = mapped_column(String(100))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    provider_message_id: Mapped[str | None]
    related_outbox_event_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("outbox_events.id", ondelete="SET NULL")
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Normalized human-readable reason, set when a delivery-status webhook
    # callback (or the initial send attempt) reports status=failed.
    failure_reason: Mapped[str | None]
