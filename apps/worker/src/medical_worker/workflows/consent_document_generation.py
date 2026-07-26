import dramatiq
import structlog

from medical_worker import broker  # noqa: F401  (registers the Redis broker)
from medical_worker.activities.generate_pdf import generate_consent_pdf

logger = structlog.get_logger(__name__)


@dramatiq.actor(max_retries=5, min_backoff=5_000, max_backoff=300_000)
def handle_consent_submitted(payload: dict) -> None:
    generate_consent_pdf.send(payload["consent_request_id"], payload["submission_id"])
