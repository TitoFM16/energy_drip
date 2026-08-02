"""Guards against a process starting up against a database schema its code
doesn't actually match — e.g. a worker container from an old build still
running after the API's newer migrations have applied, or any process
started through a path that skips `docker-entrypoint.sh`'s
`alembic upgrade head` step. Both API and worker call this at startup.

Deliberately independent of the `alembic upgrade head` step the API's own
entrypoint already runs before it starts serving traffic — that keeps a
single process's own schema up to date, but says nothing about a *second*
process (the worker) running old code against a newer schema mid-deploy, or
about any process started some other way.
"""

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine

# medical_api/core/schema_check.py -> medical_api -> src -> apps/api. Resolved
# from this file's own location rather than the process's cwd, since the API
# and worker containers run with different working directories but both
# COPY the full apps/api directory (including migrations/) to the same
# in-container path.
_MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "migrations"


class SchemaMismatchError(RuntimeError):
    pass


def _expected_head_revision() -> str:
    config = Config()
    config.set_main_option("script_location", str(_MIGRATIONS_DIR))
    return ScriptDirectory.from_config(config).get_current_head()


async def assert_schema_matches_head(engine: AsyncEngine) -> None:
    expected = _expected_head_revision()
    try:
        async with engine.connect() as connection:
            result = await connection.execute(text("SELECT version_num FROM alembic_version"))
            row = result.first()
        actual = row[0] if row else None
    except DBAPIError:
        # No alembic_version table at all — migrations have never run
        # against this database.
        actual = None
    if actual != expected:
        raise SchemaMismatchError(
            f"Database schema is at revision {actual!r} but this build expects "
            f"{expected!r}. Run `alembic upgrade head` before starting this process."
        )
