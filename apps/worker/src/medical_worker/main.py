import asyncio

from medical_api.core.database import engine
from medical_api.core.logging import configure_logging
from medical_api.core.schema_check import assert_schema_matches_head
from medical_worker.consumers.outbox import run_outbox_consumer
from medical_worker.consumers.scheduler import run_scheduler


def main() -> None:
    # Without this, structlog falls back to its default console renderer —
    # this process's logs (outbox_consumer.started, scheduler ticks, etc.)
    # would come out in a different format than the API's JSON logs, making
    # the two impossible to correlate or parse consistently downstream.
    configure_logging()
    asyncio.run(_run_all())


async def _run_all() -> None:
    # This process has no entrypoint script running `alembic upgrade head`
    # the way the API container does — nothing else guards it against
    # running old code against a newer (or unmigrated) schema.
    await assert_schema_matches_head(engine)
    await asyncio.gather(run_outbox_consumer(), run_scheduler())


if __name__ == "__main__":
    main()
