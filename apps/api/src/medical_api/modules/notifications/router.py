import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select

from medical_api.api.dependencies import AuthenticatedUser, DbSession
from medical_api.core.security import require_roles
from medical_api.modules.audit.service import AuditService
from medical_api.modules.notifications.models import NotificationMessage
from medical_api.modules.notifications.schemas import NotificationMessageRead
from medical_api.modules.notifications.service import NotificationService

router = APIRouter()

# Same staff roles that can act on the appointment a failed
# appointment_confirmation belongs to (see scheduling/router.py's
# create_appointment) — retrying a delivery isn't a more sensitive action
# than creating the appointment in the first place.
_RETRY_ROLES = ("receptionist", "assistant", "practitioner", "organization_admin")


@router.get("", response_model=list[NotificationMessageRead])
async def list_notifications(
    user: AuthenticatedUser, session: DbSession
) -> list[NotificationMessage]:
    stmt = (
        select(NotificationMessage)
        .where(NotificationMessage.organization_id == user.organization_id)
        .order_by(NotificationMessage.created_at.desc())
        .limit(100)
    )
    return list((await session.execute(stmt)).scalars().all())


@router.post(
    "/{message_id}/retry",
    response_model=NotificationMessageRead,
    dependencies=[Depends(require_roles(*_RETRY_ROLES))],
)
async def retry_notification(
    message_id: uuid.UUID, user: AuthenticatedUser, session: DbSession
) -> NotificationMessage:
    service = NotificationService(session)
    message = await service.retry(user.organization_id, message_id)
    await AuditService(session).record(
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        action="notification.retry_requested",
        resource_type="notification_message",
        resource_id=str(message.id),
        metadata={"template_key": message.template_key},
    )
    await session.commit()
    return message
