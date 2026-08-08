import uuid
from datetime import datetime

from pydantic import BaseModel

from medical_api.modules.notifications.models import (
    NotificationCategory,
    NotificationChannel,
    NotificationStatus,
)


class NotificationMessageRead(BaseModel):
    id: uuid.UUID
    channel: NotificationChannel
    category: NotificationCategory
    status: NotificationStatus
    recipient: str
    template_key: str
    failure_reason: str | None
    created_at: datetime
    sent_at: datetime | None
    delivered_at: datetime | None

    model_config = {"from_attributes": True}
