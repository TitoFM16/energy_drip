import asyncio
import uuid

import dramatiq
import structlog

from medical_api.integrations.object_storage.client import download_bytes, upload_bytes
from medical_api.integrations.pdf.generator import render_consent_pdf
from medical_api.modules.audit.service import AuditService
from medical_api.modules.consents.models import ConsentDocument
from medical_api.modules.consents.repository import ConsentRepository
from medical_api.modules.patients.repository import PatientRepository
from medical_api.shared.utilities.hashing import sha256_hash
from medical_worker import broker  # noqa: F401  (registers the Redis broker)
from medical_worker.database import async_session_factory

logger = structlog.get_logger(__name__)


@dramatiq.actor(max_retries=5, min_backoff=5_000, max_backoff=300_000)
def generate_consent_pdf(
    consent_request_id: str,
    submission_id: str,
    force_new_version: bool = False,
    reason: str | None = None,
    requested_by_user_id: str | None = None,
) -> None:
    asyncio.run(
        _generate(
            uuid.UUID(consent_request_id),
            uuid.UUID(submission_id),
            force_new_version=force_new_version,
            reason=reason,
            requested_by_user_id=uuid.UUID(requested_by_user_id) if requested_by_user_id else None,
        )
    )


async def _generate(
    consent_request_id: uuid.UUID,
    submission_id: uuid.UUID,
    *,
    force_new_version: bool = False,
    reason: str | None = None,
    requested_by_user_id: uuid.UUID | None = None,
) -> None:
    async with async_session_factory() as session:
        repository = ConsentRepository(session)

        existing_current = await repository.get_current_document_for_submission(submission_id)
        if existing_current is not None and not force_new_version:
            # The organic consent.submitted -> generate path fires exactly
            # once per submission, but dramatiq retries this actor up to 5
            # times on any transient failure (e.g. the DB commit lands but
            # the broker never gets the ack). Without this check a retry
            # would silently mint a duplicate "version" for a PDF that
            # already generated successfully.
            logger.info(
                "consent_pdf.generation_skipped_already_current",
                submission_id=str(submission_id),
                document_id=str(existing_current.id),
            )
            return

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
        # regeneration always produces a new immutable version.
        storage_key = (
            f"organizations/{request.organization_id}/patients/{request.patient_id}/"
            f"consents/{consent_request_id}/{uuid.uuid4()}.pdf"
        )
        upload_bytes(storage_key, pdf_bytes, "application/pdf")

        prior_versions = await repository.list_documents_for_submission(submission_id)
        if existing_current is not None:
            existing_current.is_current = False
        next_version = max((d.document_version for d in prior_versions), default=0) + 1

        document = await repository.create_document(
            ConsentDocument(
                submission_id=submission_id,
                storage_key=storage_key,
                sha256_hash=document_hash,
                document_version=next_version,
                regenerated_reason=reason if next_version > 1 else None,
            )
        )
        await AuditService(session).record(
            organization_id=request.organization_id,
            actor_user_id=requested_by_user_id,
            action="document.created" if next_version == 1 else "document.regenerated",
            resource_type="consent_document",
            resource_id=str(document.id),
            metadata={"document_version": next_version} | ({"reason": reason} if reason else {}),
        )
        await session.commit()
        logger.info(
            "consent_pdf.generated",
            submission_id=str(submission_id),
            document_id=str(document.id),
            document_version=next_version,
            sha256=document_hash,
        )
