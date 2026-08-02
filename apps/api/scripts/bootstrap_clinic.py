"""One-time operator bootstrap for this product's single clinic.

This product is single-tenant: there is exactly one organization, ever. The
`POST /auth/register-organization` HTTP endpoint that used to serve this
purpose is disabled in production (see `identity/router.py`) because a
public, unauthenticated route that can create organizations has no place in
a single-clinic product. Run this script once, directly against the target
database, to create that one organization and its first
`organization_admin` user.

Safe to re-run: it refuses to do anything if an organization already
exists, so it can also be used as a "is the clinic bootstrapped yet?" check
in a deploy pipeline.

Usage:
    CLINIC_NAME="My Clinic" \\
    ADMIN_EMAIL="owner@example.com" \\
    ADMIN_FULL_NAME="Owner Name" \\
    uv run python scripts/bootstrap_clinic.py

ADMIN_PASSWORD may also be set as an env var (e.g. in a deploy secret), but
prefers an interactive, non-echoed prompt so it never lands in shell
history or process listings.
"""

import asyncio
import getpass
import os
import sys

from medical_api.core.database import async_session_factory
from medical_api.core.security import hash_password
from medical_api.modules.identity.models import RoleName, User
from medical_api.modules.identity.repository import UserRepository
from medical_api.modules.organizations.models import Organization
from medical_api.modules.organizations.repository import OrganizationRepository


async def bootstrap(
    clinic_name: str, admin_email: str, admin_full_name: str, admin_password: str
) -> None:
    async with async_session_factory() as session:
        organizations = OrganizationRepository(session)
        if await organizations.exists_any():
            print("A clinic already exists in this database. Refusing to create another.")
            sys.exit(1)

        users = UserRepository(session)
        organization = Organization(name=clinic_name)
        session.add(organization)
        await session.flush()

        admin_role = await users.get_or_create_role(RoleName.ORGANIZATION_ADMIN)
        user = User(
            organization_id=organization.id,
            email=admin_email,
            hashed_password=hash_password(admin_password),
            full_name=admin_full_name,
        )
        await users.create(user)
        await users.assign_role(user.id, admin_role.id)

        await session.commit()

    print(f"Clinic '{clinic_name}' created. Admin {admin_email} can now log in.")


def main() -> None:
    clinic_name = os.environ.get("CLINIC_NAME") or input("Clinic name: ").strip()
    admin_email = os.environ.get("ADMIN_EMAIL") or input("Admin email: ").strip()
    admin_full_name = os.environ.get("ADMIN_FULL_NAME") or input("Admin full name: ").strip()
    admin_password = os.environ.get("ADMIN_PASSWORD") or getpass.getpass("Admin password: ")

    if not all([clinic_name, admin_email, admin_full_name, admin_password]):
        print("All of clinic name, admin email, full name, and password are required.")
        sys.exit(1)

    asyncio.run(bootstrap(clinic_name, admin_email, admin_full_name, admin_password))


if __name__ == "__main__":
    main()
