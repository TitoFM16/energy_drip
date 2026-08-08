import uuid
from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from medical_api.modules.identity.models import (
    PasswordResetToken,
    RefreshToken,
    Role,
    RoleName,
    User,
    UserInvite,
    UserRole,
)


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_email(self, organization_id: uuid.UUID, email: str) -> User | None:
        stmt = select(User).where(User.organization_id == organization_id, User.email == email)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_by_email_any_org(self, email: str) -> User | None:
        """Looks up a user by email without scoping to an organization.

        This product has exactly one clinic, so staff never know or need to
        supply an organization ID to log in — this is what lets the login
        and password-reset screens ask for email alone. `.limit(1)` is a
        safety net, not a real disambiguation strategy: correctness still
        relies on `uq_users_org_email` plus there only ever being one
        organization in a deployment of this product.
        """
        stmt = select(User).where(User.email == email).limit(1)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self.session.get(User, user_id)

    async def get_by_id_for_organization(
        self, organization_id: uuid.UUID, user_id: uuid.UUID
    ) -> User | None:
        stmt = select(User).where(
            User.id == user_id,
            User.organization_id == organization_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def lock_organization_users(self, organization_id: uuid.UUID) -> None:
        """Serialize role changes that could demote an organization's last admin."""
        stmt = (
            select(User.id)
            .where(User.organization_id == organization_id)
            .order_by(User.id)
            .with_for_update()
        )
        await self.session.execute(stmt)

    async def list_by_organization(self, organization_id: uuid.UUID) -> list[User]:
        stmt = select(User).where(User.organization_id == organization_id).order_by(User.full_name)
        return list((await self.session.execute(stmt)).scalars().all())

    async def create(self, user: User) -> User:
        self.session.add(user)
        await self.session.flush()
        return user

    async def get_roles(self, user_id: uuid.UUID) -> list[str]:
        stmt = (
            select(Role.name)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_or_create_role(self, name: RoleName) -> Role:
        stmt = select(Role).where(Role.name == name)
        role = (await self.session.execute(stmt)).scalar_one_or_none()
        if role is None:
            role = Role(name=name)
            self.session.add(role)
            await self.session.flush()
        return role

    async def assign_role(self, user_id: uuid.UUID, role_id: uuid.UUID) -> None:
        self.session.add(UserRole(user_id=user_id, role_id=role_id))
        await self.session.flush()

    async def replace_roles(self, user_id: uuid.UUID, role_names: list[RoleName]) -> None:
        await self.session.execute(delete(UserRole).where(UserRole.user_id == user_id))
        for role_name in role_names:
            role = await self.get_or_create_role(role_name)
            self.session.add(UserRole(user_id=user_id, role_id=role.id))
        await self.session.flush()

    async def count_users_with_role(self, organization_id: uuid.UUID, role_name: RoleName) -> int:
        stmt = (
            select(func.count(UserRole.id))
            .join(User, User.id == UserRole.user_id)
            .join(Role, Role.id == UserRole.role_id)
            .where(
                User.organization_id == organization_id,
                Role.name == role_name,
            )
        )
        return int((await self.session.execute(stmt)).scalar_one())


class RefreshTokenRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, token: RefreshToken) -> RefreshToken:
        self.session.add(token)
        await self.session.flush()
        return token

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def revoke(self, token: RefreshToken, revoked_at: datetime) -> None:
        token.revoked_at = revoked_at
        await self.session.flush()


class InviteRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, invite: UserInvite) -> UserInvite:
        self.session.add(invite)
        await self.session.flush()
        return invite

    async def get_by_token_hash(self, token_hash: str) -> UserInvite | None:
        stmt = select(UserInvite).where(UserInvite.token_hash == token_hash)
        return (await self.session.execute(stmt)).scalar_one_or_none()


class PasswordResetRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, reset_token: PasswordResetToken) -> PasswordResetToken:
        self.session.add(reset_token)
        await self.session.flush()
        return reset_token

    async def get_by_token_hash(self, token_hash: str) -> PasswordResetToken | None:
        stmt = select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
        return (await self.session.execute(stmt)).scalar_one_or_none()
