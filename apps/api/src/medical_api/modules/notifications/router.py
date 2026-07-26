from fastapi import APIRouter
from sqlalchemy import select

from medical_api.api.dependencies import AuthenticatedUser, DbSession
from medical_api.modules.notifications.models import NotificationMessage
from medical_api.modules.notifications.schemas import NotificationMessageRead

router = APIRouter()


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
