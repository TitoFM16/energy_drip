"""Direct tests for the startup schema-version guard
(core/schema_check.py). Not exercised by the other integration tests: the
FastAPI ASGI test client (`ASGITransport`) doesn't run the app's `lifespan`
by default, so `assert_schema_matches_head` — called from `main.py`'s
lifespan on every real startup — needs its own test hitting it directly.

The negative-path tests create their own short-lived, uniquely-named
database via a raw asyncpg connection rather than mutating the shared test
database's `alembic_version` table in place — this module runs against the
same database every other test file does, and corrupting that table (even
temporarily, even with a restore-in-`finally`) risks breaking whatever else
is relying on it, especially under parallel test execution.

Requires a reachable database; skips otherwise, matching every other
DB-backed test module in this directory.
"""

import uuid

import asyncpg
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from medical_api.core.config import get_settings
from medical_api.core.schema_check import SchemaMismatchError, assert_schema_matches_head

pytestmark = pytest.mark.asyncio

settings = get_settings()
# asyncpg wants a plain postgresql:// URL, not SQLAlchemy's
# postgresql+asyncpg:// driver-qualified form.
_ASYNCPG_URL = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")


async def _db_reachable() -> bool:
    try:
        conn = await asyncpg.connect(_ASYNCPG_URL)
        await conn.close()
        return True
    except Exception:
        return False


@pytest.fixture(autouse=True, scope="session")
async def _skip_without_db():
    if not await _db_reachable():
        pytest.skip("no reachable database for schema-check tests")


@pytest.fixture
async def engine():
    test_engine = create_async_engine(settings.database_url, poolclass=NullPool)
    yield test_engine
    await test_engine.dispose()


async def test_passes_when_database_is_at_head(engine):
    # The real database this test runs against is always migrated to head
    # (CI runs `alembic upgrade head` before pytest; locally whoever's
    # running this has too) — so this should simply not raise.
    await assert_schema_matches_head(engine)


@pytest.fixture
async def temp_database():
    """A short-lived, uniquely-named database on the same Postgres server,
    with no alembic_version table at all — created and dropped via
    autocommit-mode asyncpg connections, since CREATE/DROP DATABASE can't
    run inside a transaction block.
    """
    db_name = f"schema_check_test_{uuid.uuid4().hex[:12]}"
    admin_conn = await asyncpg.connect(_ASYNCPG_URL)
    try:
        await admin_conn.execute(f'CREATE DATABASE "{db_name}"')
    finally:
        await admin_conn.close()

    yield db_name

    admin_conn = await asyncpg.connect(_ASYNCPG_URL)
    try:
        await admin_conn.execute(f'DROP DATABASE IF EXISTS "{db_name}" WITH (FORCE)')
    finally:
        await admin_conn.close()


def _url_for(db_name: str) -> str:
    base = settings.database_url.rsplit("/", 1)[0]
    return f"{base}/{db_name}"


async def test_raises_when_alembic_version_table_is_missing(temp_database):
    engine = create_async_engine(_url_for(temp_database), poolclass=NullPool)
    try:
        with pytest.raises(SchemaMismatchError, match="None"):
            await assert_schema_matches_head(engine)
    finally:
        await engine.dispose()


async def test_raises_when_database_version_does_not_match_head(temp_database):
    engine = create_async_engine(_url_for(temp_database), poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
            )
            await connection.execute(
                text("INSERT INTO alembic_version VALUES ('not-a-real-revision')")
            )
        with pytest.raises(SchemaMismatchError, match="not-a-real-revision"):
            await assert_schema_matches_head(engine)
    finally:
        await engine.dispose()
