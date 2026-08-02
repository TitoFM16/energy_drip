"""Entry point for the dramatiq CLI worker process: `dramatiq medical_worker.tasks`.

Importing each module registers its `@dramatiq.actor` functions with the
broker so the CLI worker can execute them.
"""

from medical_worker.activities import (  # noqa: F401
    generate_pdf,
    send_whatsapp,
    update_delivery_status,
)
from medical_worker.workflows import (  # noqa: F401
    appointment_confirmation,
    appointment_reminders,
    consent_document_generation,
    consent_request,
    missed_appointment,
)
