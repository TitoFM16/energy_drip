import asyncio
import uuid

import dramatiq
import structlog

from medical_api.integrations.object_storage.client import download_bytes, upload_bytes
from medical_api.integrations.pdf.generator import render_consent_pdf, sha256_hash
from medical_api.modules.consents.models import ConsentDocument
from medical_api.modules.consents.repository import ConsentRepository
from medical_api.modules.patients.repository import PatientRepository
from medical_worker import broker  # noqa: F401  (registers the Redis broker)
from medical_worker.database import async_session_factory

logger = structlog.get_logger(__name__)


@dramatiq.actor(max_retries=5, min_backoff=5_000, max_backoff=300_000)
def generate_consent_pdf(consent_request_id: str, submission_id: str) -> None:
    asyncio.run(_generate(uuid.UUID(consent_request_id), uuid.UUID(submission_id)))


async def _generate(consent_request_id: uuid.UUID, submission_id: uuid.UUID) -> None:
    async with async_session_factory() as session:
        repository = ConsentRepository(session)
        request = await repository.get_request(consent_request_id)
        submission = await repository.get_submission(submission_id)
        signature = await repository.get_signature(submission_id)
        answers = await repository.list_answers(submission_id)
        version = await repository.get_template_version(request.template_version_id)
        patient = await PatientRepository(session).get(request.organization_id, request.patient_id)

        signature_svg = download_bytes(signature.signature_svg_path).decode()
        pdf_bytes = render_consent_pdf(
            patient_name=f"{patient.first_name} {patient.last_name}",
            template_body_markdown=version.body_markdown if version else "",
            answers=[{"field_key": a.field_key, "value": a.value.get("value")} for a in answers],
            signature_svg=signature_svg,
            signed_at=submission.submitted_at,
            ip_address=submission.ip_address,
        )
        document_hash = sha256_hash(pdf_bytes)

        # Storage is never overwritten: each generation gets a fresh key, so
        # "regeneration" always produces a new immutable version.
        storage_key = (
            f"organizations/{request.organization_id}/patients/{request.patient_id}/"
            f"consents/{consent_request_id}/{uuid.uuid4()}.pdf"
        )
        upload_bytes(storage_key, pdf_bytes, "application/pdf")

        await repository.create_document(
            ConsentDocument(
                submission_id=submission_id, storage_key=storage_key, sha256_hash=document_hash
            )
        )
        await session.commit()
        logger.info("consent_pdf.generated", submission_id=str(submission_id), sha256=document_hash)
