import asyncio

from medical_worker.consumers.outbox import run_outbox_consumer


def main() -> None:
    asyncio.run(run_outbox_consumer())


if __name__ == "__main__":
    main()
