"""Private document permissions, expiring downloads and inline PDF regeneration."""

import importlib.util
import io
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from PIL import Image
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
    ConsentSignature,
    ConsentSubmission,
    ConsentTemplate,
    ConsentTemplateVersion,
    EligibilityResult,
)
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

    signature_key = f"organizations/{organization_id}/documents-test/{uuid.uuid4()}.svg"
    upload_bytes(
        signature_key,
        b'<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100">'
        b'<path d="M10 10 L100 50" stroke="black"/></svg>',
        "image/svg+xml",
    )
    session.add(ConsentSignature(submission_id=submission.id, signature_svg_path=signature_key))
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

    fetched = await client.get(body["url"])
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


async def test_regenerate_creates_new_pdf_immediately(client):
    org = await _register_org(client)
    admin_headers = {"Authorization": f"Bearer {org['access_token']}"}
    seeded = await _seed_document(client.db_session, uuid.UUID(org["organization_id"]))
    response = await client.post(
        f"/api/v1/documents/{seeded['document_id']}/regenerate",
        json={"reason": "Improve original PDF rendering"},
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    original = await client.db_session.get(ConsentDocument, seeded["document_id"])
    assert original.is_current is False
    documents = (
        (
            await client.db_session.execute(
                select(ConsentDocument)
                .where(ConsentDocument.submission_id == original.submission_id)
                .order_by(ConsentDocument.document_version)
            )
        )
        .scalars()
        .all()
    )
    assert len(documents) == 2
    assert documents[1].is_current is True
    assert documents[1].regenerated_reason == "Improve original PDF rendering"
    download = await client.get(
        f"/api/v1/documents/{documents[1].id}/download", headers=admin_headers
    )
    content = await client.get(download.json()["url"])
    assert content.content.startswith(b"%PDF-")
    verified = await client.post(
        f"/api/v1/documents/{documents[1].id}/verify", headers=admin_headers
    )
    assert verified.json()["matches"] is True


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


async def test_service_image_upload_is_owned_role_gated_and_rejects_active_content(client):
    owner = await _register_org(client)
    headers = {"Authorization": f"Bearer {owner['access_token']}"}
    service = await client.post(
        "/api/v1/treatments/definitions",
        json={"name": "Consulta", "price": "50000"},
        headers=headers,
    )
    assert service.status_code == 201, service.text
    path = f"/api/v1/treatments/definitions/{service.json()['id']}/image"
    image = io.BytesIO()
    Image.new("RGB", (32, 32), "blue").save(image, format="PNG")
    files = {"file": ("photo.png", image.getvalue(), "image/png")}
    assert (await client.post(path, files=files)).status_code == 401
    other = await _register_org(client)
    assert (
        await client.post(
            path, files=files, headers={"Authorization": f"Bearer {other['access_token']}"}
        )
    ).status_code == 404
    worker = await _invite_and_accept(client, headers, "practitioner")
    assert (
        await client.post(
            path, files=files, headers={"Authorization": f"Bearer {worker['access_token']}"}
        )
    ).status_code == 403
    bad_image = await client.post(
        path,
        headers=headers,
        files={"file": ("photo.svg", b"<svg><script>alert(1)</script></svg>", "image/svg+xml")},
    )
    assert bad_image.status_code == 422
    uploaded = await client.post(path, headers=headers, files=files)
    assert uploaded.status_code == 200, uploaded.text
    assert uploaded.json()["image_url"].startswith("/media/services/")
    public_image = await client.get(uploaded.json()["image_url"])
    assert public_image.status_code == 200
    assert public_image.headers["content-type"] == "image/webp"


async def test_operator_recovery_is_scoped_revokes_refresh_and_keeps_new_login(client):
    script = Path(__file__).parents[1] / "scripts" / "reset_staff_password.py"
    spec = importlib.util.spec_from_file_location("reset_staff_password", script)
    recovery = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(recovery)
    registered = await _register_org(client)
    headers = {"Authorization": f"Bearer {registered['access_token']}"}
    profile = await client.get("/api/v1/auth/me", headers=headers)
    email = profile.json()["email"]
    pending_reset = await client.post("/api/v1/auth/password-reset/request", json={"email": email})
    with pytest.raises(ValueError):
        await recovery.reset_user_password(
            client.db_session,
            organization_id=uuid.uuid4(),
            email=email,
            password="new-owner-password-123",
        )
    await recovery.reset_user_password(
        client.db_session,
        organization_id=uuid.UUID(registered["organization_id"]),
        email=email,
        password="new-owner-password-123",
    )
    await client.db_session.commit()
    old_login = await client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "supersecret123",
        },
    )
    assert old_login.status_code == 401
    new_login = await client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "new-owner-password-123",
        },
    )
    assert new_login.status_code == 200
    refresh = await client.post(
        "/api/v1/auth/refresh",
        json={
            "refresh_token": registered["refresh_token"],
        },
    )
    assert refresh.status_code == 401
    reset_attempt = await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={
            "token": pending_reset.json()["token"],
            "new_password": "another-password-123",
        },
    )
    assert reset_attempt.status_code == 400
    events = await client.get("/api/v1/audit", headers=headers)
    assert any(event["action"] == "user.password_reset_by_operator" for event in events.json())
