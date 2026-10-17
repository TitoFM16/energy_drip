"""Shared-role creation remains safe while another transaction owns the unique key."""

import asyncio
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import MetaData, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.schema import CreateSchema, DropSchema

from medical_api.core.database import engine
from medical_api.modules.identity.models import Role, RoleName
from medical_api.modules.identity.repository import UserRepository

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest_asyncio.fixture(loop_scope="session")
async def isolated_roles_schema():
    # Isolate the shared roles table so this test neither deletes live roles
    # nor depends on whether another test already created PRACTITIONER.
    schema = f"test_role_race_{uuid.uuid4().hex}"
    metadata = MetaData()
    Role.__table__.to_metadata(metadata, schema=schema)
    async with engine.begin() as connection:
        await connection.execute(CreateSchema(schema))
        await connection.run_sync(metadata.create_all)
    try:
        yield schema
    finally:
        async with engine.begin() as connection:
            await connection.execute(DropSchema(schema, cascade=True))


@pytest.mark.parametrize("winner_commits", [True, False])
async def test_get_or_create_role_waits_for_concurrent_insert(
    isolated_roles_schema, winner_commits
):
    schema = isolated_roles_schema
    async with AsyncSession(engine, expire_on_commit=False) as first:
        # set_config is parameterized and LOCAL, so pooled connections cannot
        # retain the test search path after commit/rollback.
        await first.execute(
            text("SELECT set_config('search_path', :schema, true)"), {"schema": f"{schema},public"}
        )
        first_pid = await first.scalar(text("SELECT pg_backend_pid()"))
        first_role = await UserRepository(first).get_or_create_role(RoleName.PRACTITIONER)
        first_id = first_role.id
        second_pid_ready = asyncio.get_running_loop().create_future()

        async def competing_insert():
            async with AsyncSession(engine, expire_on_commit=False) as second:
                await second.execute(
                    text("SELECT set_config('search_path', :schema, true)"),
                    {"schema": f"{schema},public"},
                )
                second_pid_ready.set_result(await second.scalar(text("SELECT pg_backend_pid()")))
                role = await UserRepository(second).get_or_create_role(RoleName.PRACTITIONER)
                await second.commit()
                return role.id

        contender = asyncio.create_task(competing_insert())
        try:
            async with asyncio.timeout(10):
                second_pid = await second_pid_ready
                # Verify actual PostgreSQL lock contention rather than hoping
                # two coroutine calls happen to interleave in a particular order.
                # Database lock state has no in-process Event to await.
                while first_pid not in await first.scalar(  # noqa: ASYNC110
                    text("SELECT pg_blocking_pids(:pid)"), {"pid": second_pid}
                ):
                    await asyncio.sleep(0.01)
                assert not contender.done()
                if winner_commits:
                    await first.commit()
                else:
                    await first.rollback()
                second_id = await contender
            if winner_commits:
                assert second_id == first_id
            else:
                assert second_id != first_id
            await first.execute(
                text("SELECT set_config('search_path', :schema, true)"),
                {"schema": f"{schema},public"},
            )
            assert await first.scalar(select(func.count()).select_from(Role)) == 1
            assert (await first.scalars(select(Role))).one().id == second_id
        finally:
            if not contender.done():
                contender.cancel()
            await asyncio.gather(contender, return_exceptions=True)
