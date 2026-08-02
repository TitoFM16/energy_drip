"""A separate, NullPool-backed session factory for dramatiq actors.

Actors run in dramatiq's worker thread pool, and each actor invocation
wraps its async work in its own `asyncio.run(...)` call — a fresh event
loop every time. `medical_api.core.database`'s pooled `engine` is sized
for a single long-lived event loop (the API's uvicorn process); handing a
connection checked into that pool by one event loop to a different loop —
which happens routinely here, since dramatiq round-robins actor calls
across worker threads — raises asyncpg's "got Future attached to a
different loop" (discovered live while testing the WhatsApp delivery
webhook: two sequential webhook-triggered actor calls were enough to hit
it, so this affects every actor, not just the new one).

`consumers/outbox.py` doesn't need this: `run_outbox_consumer()` runs one
continuous `while True` loop for the whole process's life via a single
`asyncio.run()` in `main.py`, so it never hands a connection across loops.
Every `@dramatiq.actor`-decorated function elsewhere in this package does.

NullPool sidesteps the problem by never reusing a connection across
checkouts — each actor call gets a fresh physical connection and closes it
when done. The connection-setup overhead is negligible at this app's
actor call volume (appointment/consent/reminder/webhook events, not a hot
request path).
"""

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from medical_api.core.config import get_settings

settings = get_settings()

worker_engine = create_async_engine(settings.database_url, poolclass=NullPool)
async_session_factory = async_sessionmaker(worker_engine, expire_on_commit=False)
