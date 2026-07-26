import uuid
from datetime import datetime

from pydantic import BaseModel

from medical_api.modules.notifications.models import NotificationChannel, NotificationStatus


class NotificationMessageRead(BaseModel):
    id: uuid.UUID
    channel: NotificationChannel
    status: NotificationStatus
    recipient: str
    template_key: str
    sent_at: datetime | None
    delivered_at: datetime | None

    model_config = {"from_attributes": True}
