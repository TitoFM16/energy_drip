"""Coverage for "Document access, verification, and invalidation" and the
version-tracking half of "Document version history and regeneration" in
missing_features.md. Same real-database-plus-savepoint pattern as
test_operational_dashboard.py — see that module's docstring, and
test_auth_flows.py's `client` fixture, for the full rationale.

PDF generation itself happens asynchronously in the worker (see
apps/worker/src/medical_worker/activities/generate_pdf.py) and isn't
exercised by this pytest suite (no worker process runs alongside the
ASGI test client) — the fixture below inserts a ConsentDocument row and a
real object directly, uploaded through the same `upload_bytes` the worker
uses, so download/verify hit real MinIO rather than a mock. The
regenerate endpoint's actual PDF regeneration was verified live against
the real docker compose stack with the worker running (see
missing_features.md's writeup) — this suite only covers the API-layer
authorization/enqueue/audit behavior it's actually responsible for.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from medical_api.core.config import get_settings
from medical_api.core.database import engine, get_db
from medical_api.integrations.object_storage.client import upload_bytes
from medical_api.main import app
from medical_api.modules.consents.models import (
    ConsentDocument,
    ConsentRequest,
    ConsentRequestStatus,
    ConsentSubmission,
    ConsentTemplate,
    ConsentTemplateVersion,
    EligibilityResult,
)
from medical_api.modules.notifications.models import OutboxEvent
from medical_api.modules.patients.models import Patient
from medical_api.shared.utilities.hashing import sha256_hash

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest_asyncio.fixture(loop_scope="session")
async def client():
    connection = await engine.connect()
    outer_transaction = await connection.begin()
    session = AsyncSession(
        bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )

    async def override_get_db():
        try:
            yield session
        except Exception:
            await session.rollback()
            raise

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as async_client:
            async_client.db_session = session
            yield async_client
    finally:
        del app.dependency_overrides[get_db]
        await session.close()
        await outer_transaction.rollback()
        await connection.close()


async def _db_reachable() -> bool:
    probe_engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
    try:
        async with probe_engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
    finally:
        await probe_engine.dispose()


@pytest.fixture(autouse=True, scope="session")
async def _skip_without_db():
    if not await _db_reachable():
        pytest.skip("no reachable database for documents integration tests")


async def _register_org(client) -> dict:
    response = await client.post(
        "/api/v1/auth/register-organization",
        json={
            "organization_name": f"Documents Clinic {uuid.uuid4()}",
            "admin_email": f"documents-{uuid.uuid4()}@example.com",
            "admin_password": "supersecret123",
            "admin_full_name": "Documents Admin",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _invite_and_accept(client, admin_headers: dict, role: str) -> dict:
    email = f"{role}-{uuid.uuid4()}@example.com"
    invite = await client.post(
        "/api/v1/auth/invites", json={"email": email, "role": role}, headers=admin_headers
    )
    assert invite.status_code == 201, invite.text
    accept = await client.post(
        f"/api/v1/auth/invites/{invite.json()['token']}/accept",
        json={"full_name": role.title(), "password": "somesecretpw123"},
    )
    assert accept.status_code == 201, accept.text
    return accept.json()


async def _seed_document(
    session, organization_id: uuid.UUID, *, pdf_bytes: bytes = b"%PDF-1.4 test"
) -> dict:
    now = datetime.now(UTC)
    patient = Patient(
        organization_id=organization_id,
        first_name="Rosa",
        last_name="Documents",
        document_id=f"doc-{uuid.uuid4()}",
        date_of_birth=None,
        phone_number="+573001112233",
        email=None,
    )
    template = ConsentTemplate(organization_id=organization_id, name="Documents consent")
    session.add_all([patient, template])
    await session.flush()

    template_version = ConsentTemplateVersion(
        template_id=template.id,
        version_number=1,
        published_at=now,
        body_markdown="Consiento el tratamiento.",
    )
    session.add(template_version)
    await session.flush()

    request = ConsentRequest(
        organization_id=organization_id,
        patient_id=patient.id,
        appointment_id=None,
        template_version_id=template_version.id,
        token_hash=sha256_hash(uuid.uuid4().bytes),
        status=ConsentRequestStatus.COMPLETED,
        expires_at=now + timedelta(hours=24),
    )
    session.add(request)
    await session.flush()

    submission = ConsentSubmission(
        consent_request_id=request.id,
        timezone="America/Bogota",
        ip_address="127.0.0.1",
        user_agent="pytest",
        eligibility_result=EligibilityResult.ELIGIBLE,
    )
    session.add(submission)
    await session.flush()

    storage_key = f"organizations/{organization_id}/documents-test/{uuid.uuid4()}.pdf"
    upload_bytes(storage_key, pdf_bytes, "application/pdf")
    document = ConsentDocument(
        submission_id=submission.id,
        storage_key=storage_key,
        sha256_hash=sha256_hash(pdf_bytes),
        document_version=1,
    )
    session.add(document)
    await session.flush()
    await session.commit()

    return {"patient_id": patient.id, "request_id": request.id, "document_id": document.id}


async def test_document_is_org_scoped_and_role_gated(client):
    org_a = await _register_org(client)
    admin_a_headers = {"Authorization": f"Bearer {org_a['access_token']}"}
    receptionist_a = await _invite_and_accept(client, admin_a_headers, "receptionist")
    receptionist_a_headers = {"Authorization": f"Bearer {receptionist_a['access_token']}"}

    org_b = await _register_org(client)
    admin_b_headers = {"Authorization": f"Bearer {org_b['access_token']}"}

    seeded = await _seed_document(client.db_session, uuid.UUID(org_a["organization_id"]))
    document_id = seeded["document_id"]

    reception_read = await client.get(
        f"/api/v1/documents/{document_id}", headers=receptionist_a_headers
    )
    assert reception_read.status_code == 403

    cross_org_read = await client.get(f"/api/v1/documents/{document_id}", headers=admin_b_headers)
    assert cross_org_read.status_code == 404

    own_org_read = await client.get(f"/api/v1/documents/{document_id}", headers=admin_a_headers)
    assert own_org_read.status_code == 200, own_org_read.text
    assert own_org_read.json()["is_current"] is True
    assert own_org_read.json()["invalidated_at"] is None


async def test_download_returns_a_working_presigned_url(client):
    org = await _register_org(client)
    admin_headers = {"Authorization": f"Bearer {org['access_token']}"}
    pdf_bytes = b"%PDF-1.4 download test content"
    seeded = await _seed_document(
        client.db_session, uuid.UUID(org["organization_id"]), pdf_bytes=pdf_bytes
    )

    download = await client.get(
        f"/api/v1/documents/{seeded['document_id']}/download", headers=admin_headers
    )
    assert download.status_code == 200, download.text
    body = download.json()
    assert body["expires_in"] > 0

    async with AsyncClient() as raw_client:
        fetched = await raw_client.get(body["url"])
    assert fetched.status_code == 200
    assert fetched.content == pdf_bytes


async def test_verify_detects_a_tampered_stored_hash(client):
    org = await _register_org(client)
    admin_headers = {"Authorization": f"Bearer {org['access_token']}"}
    seeded = await _seed_document(client.db_session, uuid.UUID(org["organization_id"]))

    verify = await client.post(
        f"/api/v1/documents/{seeded['document_id']}/verify", headers=admin_headers
    )
    assert verify.status_code == 200, verify.text
    assert verify.json()["matches"] is True

    # Simulate the stored hash no longer matching the object (corruption,
    # tampering) — verify must catch it, not just echo the stored value.
    document = await client.db_session.get(ConsentDocument, seeded["document_id"])
    document.sha256_hash = "0" * 64
    await client.db_session.commit()

    verify_after_tamper = await client.post(
        f"/api/v1/documents/{seeded['document_id']}/verify", headers=admin_headers
    )
    assert verify_after_tamper.status_code == 200, verify_after_tamper.text
    assert verify_after_tamper.json()["matches"] is False


async def test_invalidate_requires_a_designated_role_and_is_one_way(client):
    org = await _register_org(client)
    admin_headers = {"Authorization": f"Bearer {org['access_token']}"}
    practitioner = await _invite_and_accept(client, admin_headers, "practitioner")
    practitioner_headers = {"Authorization": f"Bearer {practitioner['access_token']}"}
    seeded = await _seed_document(client.db_session, uuid.UUID(org["organization_id"]))
    document_id = seeded["document_id"]

    # A plain practitioner can read/download/verify but not invalidate —
    # invalidating a signed legal document is a bigger, more deliberate
    # action than the rest.
    practitioner_attempt = await client.post(
        f"/api/v1/documents/{document_id}/invalidate",
        json={"reason": "Testing role gate"},
        headers=practitioner_headers,
    )
    assert practitioner_attempt.status_code == 403

    invalidated = await client.post(
        f"/api/v1/documents/{document_id}/invalidate",
        json={"reason": "Duplicate submission, wrong patient linked"},
        headers=admin_headers,
    )
    assert invalidated.status_code == 200, invalidated.text
    assert invalidated.json()["invalidated_at"] is not None
    assert invalidated.json()["invalidated_reason"] == "Duplicate submission, wrong patient linked"

    already_invalidated = await client.post(
        f"/api/v1/documents/{document_id}/invalidate",
        json={"reason": "Trying again"},
        headers=admin_headers,
    )
    assert already_invalidated.status_code == 409


async def test_regenerate_enqueues_a_worker_event(client):
    org = await _register_org(client)
    admin_headers = {"Authorization": f"Bearer {org['access_token']}"}
    seeded = await _seed_document(client.db_session, uuid.UUID(org["organization_id"]))

    regenerate = await client.post(
        f"/api/v1/documents/{seeded['document_id']}/regenerate",
        json={"reason": "Original PDF failed to render correctly"},
        headers=admin_headers,
    )
    assert regenerate.status_code == 202, regenerate.text

    # Scoped to this test's own organization — READ COMMITTED means this
    # query would otherwise also see real outbox_events rows genuinely
    # committed by other connections against the same shared dev database
    # (e.g. the docker compose worker/other manual testing), not just
    # this test's own savepoint-scoped writes.
    stmt = select(OutboxEvent).where(
        OutboxEvent.event_type == "consent.document.regenerate_requested",
        OutboxEvent.organization_id == uuid.UUID(org["organization_id"]),
    )
    events = (await client.db_session.execute(stmt)).scalars().all()
    assert len(events) == 1
    assert events[0].payload["reason"] == "Original PDF failed to render correctly"
    assert events[0].payload["submission_id"] is not None


async def test_document_mutations_are_audited(client):
    org = await _register_org(client)
    admin_headers = {"Authorization": f"Bearer {org['access_token']}"}
    seeded = await _seed_document(client.db_session, uuid.UUID(org["organization_id"]))
    document_id = seeded["document_id"]

    await client.get(f"/api/v1/documents/{document_id}", headers=admin_headers)
    await client.get(f"/api/v1/documents/{document_id}/download", headers=admin_headers)
    await client.post(f"/api/v1/documents/{document_id}/verify", headers=admin_headers)
    await client.post(
        f"/api/v1/documents/{document_id}/invalidate",
        json={"reason": "Audit coverage test"},
        headers=admin_headers,
    )

    audit_events = await client.get("/api/v1/audit", headers=admin_headers)
    assert audit_events.status_code == 200
    actions = {e["action"] for e in audit_events.json() if e["resource_id"] == str(document_id)}
    assert actions == {
        "document.accessed",
        "document.downloaded",
        "document.verified",
        "document.invalidated",
    }
