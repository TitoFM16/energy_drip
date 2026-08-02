import asyncio

from medical_worker.consumers.outbox import run_outbox_consumer
from medical_worker.consumers.scheduler import run_scheduler


def main() -> None:
    asyncio.run(_run_all())


async def _run_all() -> None:
    await asyncio.gather(run_outbox_consumer(), run_scheduler())


if __name__ == "__main__":
    main()
