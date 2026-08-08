"""Authorization, finality, org scoping, and audit coverage for consent reviews.

These tests use the same real-PostgreSQL transaction/savepoint fixture as
test_authorization_and_audit.py; no repositories or authorization checks are
mocked.
"""

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from medical_api.core.config import get_settings
from medical_api.core.database import engine, get_db
from medical_api.main import app
from medical_api.modules.audit.models import AuditEvent

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest_asyncio.fixture(loop_scope="session")
async def client():
    connection = await engine.connect()
    outer_transaction = await connection.begin()
    session = AsyncSession(
        bind=connection,
        join_transaction_mode="create_savepoint",
        expire_on_commit=False,
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
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ac.db_session = session
            yield ac
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
        pytest.skip("no reachable database for consent review integration tests")


async def _register_org(client: AsyncClient) -> dict:
    response = await client.post(
        "/api/v1/auth/register-organization",
        json={
            "organization_name": f"Review Clinic {uuid.uuid4()}",
            "admin_email": f"admin-{uuid.uuid4()}@example.com",
            "admin_password": "supersecret123",
            "admin_full_name": "Review Admin",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _invite_and_accept(
    client: AsyncClient,
    admin_headers: dict[str, str],
    role: str,
    full_name: str,
) -> dict:
    invite = await client.post(
        "/api/v1/auth/invites",
        json={"email": f"{role}-{uuid.uuid4()}@example.com", "role": role},
        headers=admin_headers,
    )
    assert invite.status_code == 201, invite.text
    accepted = await client.post(
        f"/api/v1/auth/invites/{invite.json()['token']}/accept",
        json={"full_name": full_name, "password": "somesecretpw123"},
    )
    assert accepted.status_code == 201, accepted.text
    return accepted.json()


async def _create_manual_review_submission(
    client: AsyncClient, admin_headers: dict[str, str]
) -> tuple[str, str]:
    patient = await client.post(
        "/api/v1/patients",
        json={
            "first_name": "María",
            "last_name": "Revisión",
            "phone_number": "+573001112233",
        },
        headers=admin_headers,
    )
    assert patient.status_code == 201, patient.text

    template = await client.post(
        "/api/v1/consents/templates",
        json={
            "name": "Manual review template",
            "body_markdown": "Consent text",
            "questions": [
                {
                    "field_key": "has_condition",
                    "prompt": "¿Tiene alguna condición activa?",
                    "question_type": "boolean",
                    "display_order": 0,
                    "is_required": True,
                    "options": [],
                }
            ],
        },
        headers=admin_headers,
    )
    assert template.status_code == 201, template.text
    template_id = template.json()["id"]
    version_id = template.json()["latest_version"]["id"]
    published = await client.post(
        f"/api/v1/consents/templates/{template_id}/versions/{version_id}/publish",
        headers=admin_headers,
    )
    assert published.status_code == 200, published.text

    consent_request = await client.post(
        "/api/v1/consents/requests",
        params={
            "patient_id": patient.json()["id"],
            "template_version_id": version_id,
        },
        headers=admin_headers,
    )
    assert consent_request.status_code == 201, consent_request.text
    token = consent_request.json()["token"]
    request_id = consent_request.json()["consent_request_id"]

    form = await client.get(f"/api/v1/public/consents/{token}")
    assert form.status_code == 200, form.text
    question = form.json()["questions"][0]
    submitted = await client.post(
        f"/api/v1/public/consents/{token}/submit",
        json={
            "answers": [
                {
                    "question_id": question["id"],
                    "field_key": question["field_key"],
                    "value": True,
                }
            ],
            "signature_svg": "<svg></svg>",
            "timezone": "America/Bogota",
        },
    )
    assert submitted.status_code == 201, submitted.text
    assert submitted.json()["eligibility_result"] == "requires_manual_review"
    return request_id, submitted.json()["submission_id"]


async def test_review_decision_is_role_gated_and_organization_scoped(client):
    org = await _register_org(client)
    admin_headers = {"Authorization": f"Bearer {org['access_token']}"}
    _, submission_id = await _create_manual_review_submission(client, admin_headers)
    receptionist = await _invite_and_accept(
        client, admin_headers, "receptionist", "Review Receptionist"
    )

    forbidden = await client.post(
        f"/api/v1/consents/submissions/{submission_id}/review",
        json={"decision": "approved", "rationale": "Reviewed clinically"},
        headers={"Authorization": f"Bearer {receptionist['access_token']}"},
    )
    assert forbidden.status_code == 403

    other_org = await _register_org(client)
    cross_org = await client.post(
        f"/api/v1/consents/submissions/{submission_id}/review",
        json={"decision": "approved", "rationale": "Should not be visible"},
        headers={"Authorization": f"Bearer {other_org['access_token']}"},
    )
    assert cross_org.status_code == 404


async def test_review_decision_is_one_way_and_audited(client):
    org = await _register_org(client)
    organization_id = uuid.UUID(org["organization_id"])
    admin_headers = {"Authorization": f"Bearer {org['access_token']}"}
    request_id, submission_id = await _create_manual_review_submission(client, admin_headers)
    practitioner = await _invite_and_accept(client, admin_headers, "practitioner", "Dra. Revisora")
    practitioner_headers = {"Authorization": f"Bearer {practitioner['access_token']}"}

    reviewed = await client.post(
        f"/api/v1/consents/submissions/{submission_id}/review",
        json={"decision": "approved", "rationale": "  Sin contraindicación clínica.  "},
        headers=practitioner_headers,
    )
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["decision"] == "approved"
    assert reviewed.json()["rationale"] == "Sin contraindicación clínica."
    assert reviewed.json()["reviewed_by_name"] == "Dra. Revisora"
    assert reviewed.json()["reviewed_at"] is not None

    overwrite = await client.post(
        f"/api/v1/consents/submissions/{submission_id}/review",
        json={"decision": "rejected", "rationale": "Changed silently"},
        headers=practitioner_headers,
    )
    assert overwrite.status_code == 409
    assert "already been reviewed" in overwrite.json()["detail"]

    detail = await client.get(f"/api/v1/consents/requests/{request_id}", headers=admin_headers)
    assert detail.status_code == 200, detail.text
    submission = detail.json()["submission"]
    assert submission["review_decision"] == "approved"
    assert submission["review_rationale"] == "Sin contraindicación clínica."
    assert submission["reviewed_by_name"] == "Dra. Revisora"

    review_queue = await client.get(
        "/api/v1/consents/requests",
        params={"needs_review": "true"},
        headers=admin_headers,
    )
    assert review_queue.status_code == 200, review_queue.text
    assert all(item["id"] != request_id for item in review_queue.json())

    stmt = select(AuditEvent).where(
        AuditEvent.organization_id == organization_id,
        AuditEvent.action == "consent_submission.reviewed",
        AuditEvent.resource_id == submission_id,
    )
    event = (await client.db_session.execute(stmt)).scalar_one()
    assert event.event_metadata == {
        "decision": "approved",
        "rationale": "Sin contraindicación clínica.",
    }
