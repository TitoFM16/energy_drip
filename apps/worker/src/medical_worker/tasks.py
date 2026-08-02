"""Entry point for the dramatiq CLI worker process: `dramatiq medical_worker.tasks`.

Importing each module registers its `@dramatiq.actor` functions with the
broker so the CLI worker can execute them.
"""

import asyncio

from medical_api.core.logging import configure_logging
from medical_api.core.schema_check import assert_schema_matches_head
from medical_worker.database import worker_engine

# Module-level, not inside a function: dramatiq's CLI imports this module
# once at process startup and never calls back into it, so this is the
# only hook available to configure logging (and check the schema, below)
# before any actor runs. Without it this process's logs use structlog's
# default console renderer instead of the same JSON format as the API and
# the other worker process (medical_worker.main), making the three
# impossible to correlate.
configure_logging()

# Same guard as medical_worker.main — this process has no entrypoint
# script of its own to run migrations first, and dramatiq gives no async
# startup hook, so this one-shot event loop at import time is the only
# place to put it. Uses worker_engine (NullPool), not medical_api's pooled
# engine — see medical_worker/database.py's docstring: a pooled connection
# created under this throwaway asyncio.run() loop would get reused by a
# dramatiq actor's own asyncio.run() loop later and crash with "attached
# to a different loop", the exact bug that module exists to avoid.
asyncio.run(assert_schema_matches_head(worker_engine))

from medical_worker.activities import (  # noqa: F401, E402
    generate_pdf,
    send_whatsapp,
    update_delivery_status,
)
from medical_worker.workflows import (  # noqa: F401, E402
    appointment_confirmation,
    appointment_reminders,
    consent_document_generation,
    consent_request,
    missed_appointment,
)
