"""Operator recovery without email delivery. Run inside the API container.

Prompts for the exact account email, clinic UUID (unless configured), and
new password twice without echo. Passwords are never command arguments.
"""

import asyncio
import getpass
import sys
import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from medical_api.core.config import get_settings
from medical_api.core.database import async_session_factory
from medical_api.core.security import hash_password
from medical_api.modules.audit.service import AuditService
from medical_api.modules.identity.models import PasswordResetToken, RefreshToken, User


def validate_password(password: str) -> None:
    if len(password) < 12 or len(password.encode("utf-8")) > 72:
        raise ValueError("Use at least 12 characters and no more than 72 UTF-8 bytes.")


async def reset_user_password(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    email: str,
    password: str,
) -> uuid.UUID:
    validate_password(password)
    user = (
        await session.execute(
            select(User)
            .where(
                User.organization_id == organization_id,
                User.email == email,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if user is None or not user.is_active:
        raise ValueError("No active account matches that exact email and clinic UUID.")
    user.hashed_password = hash_password(password)
    now = datetime.now(UTC)
    await session.execute(
        update(RefreshToken)
        .where(
            RefreshToken.user_id == user.id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
    await session.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        )
        .values(used_at=now)
    )
    await AuditService(session).record(
        organization_id=organization_id,
        actor_user_id=None,
        action="user.password_reset_by_operator",
        resource_type="user",
        resource_id=str(user.id),
    )
    await session.flush()
    return user.id


async def recover(organization_id: uuid.UUID, email: str, password: str) -> None:
    async with async_session_factory() as session:
        await reset_user_password(
            session,
            organization_id=organization_id,
            email=email,
            password=password,
        )
        await session.commit()


def main() -> None:
    try:
        organization_id = get_settings().public_organization_id
        if organization_id is None:
            organization_id = uuid.UUID(input("Clinic UUID: ").strip())
        print(f"Clinic: {organization_id}")
        email = input("Exact account email: ").strip()
        password = getpass.getpass("New password (at least 12 characters): ")
        validate_password(password)
        if password != getpass.getpass("Repeat new password: "):
            raise ValueError("Passwords do not match.")
        asyncio.run(recover(organization_id, email, password))
    except (ValueError, EOFError) as exc:
        print(f"Recovery stopped: {exc}", file=sys.stderr)
        sys.exit(1)
    print("Password changed. Refresh sessions and pending reset links revoked.")
    print(
        "Previously issued access tokens expire within "
        f"{get_settings().access_token_expire_minutes} minutes."
    )


if __name__ == "__main__":
    main()
