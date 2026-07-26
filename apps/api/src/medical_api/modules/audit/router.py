from fastapi import APIRouter, Depends
from sqlalchemy import select

from medical_api.api.dependencies import AuthenticatedUser, DbSession
from medical_api.core.security import require_roles
from medical_api.modules.audit.models import AuditEvent
from medical_api.modules.audit.schemas import AuditEventRead

router = APIRouter(
    dependencies=[Depends(require_roles("auditor", "organization_admin", "platform_admin"))]
)


@router.get("", response_model=list[AuditEventRead])
async def list_audit_events(user: AuthenticatedUser, session: DbSession) -> list[AuditEvent]:
    stmt = (
        select(AuditEvent)
        .where(AuditEvent.organization_id == user.organization_id)
        .order_by(AuditEvent.occurred_at.desc())
        .limit(100)
    )
    return list((await session.execute(stmt)).scalars().all())
