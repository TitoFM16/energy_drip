"""Coverage for the consent-request lifecycle gap in missing_features.md:
resend, revoke (invalidate with a reason), and clear per-state errors on
the patient-facing form endpoint. Same real-database-plus-savepoint
pattern as test_authorization_and_audit.py / test_operational_dashboard.py
— see those modules' docstrings for the full rationale.
"""

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from medical_api.core.config import get_settings
from medical_api.core.database import engine, get_db
from medical_api.main import app

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
        pytest.skip("no reachable database for consent-lifecycle integration tests")


async def _register_org(client) -> dict:
    response = await client.post(
        "/api/v1/auth/register-organization",
        json={
            "organization_name": f"Lifecycle Clinic {uuid.uuid4()}",
            "admin_email": f"lifecycle-{uuid.uuid4()}@example.com",
            "admin_password": "supersecret123",
            "admin_full_name": "Lifecycle Admin",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _create_patient(client, headers: dict) -> str:
    response = await client.post(
        "/api/v1/patients",
        json={"first_name": "Jane", "last_name": "Doe", "phone_number": "+573001112233"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def _published_template_version(client, headers: dict) -> str:
    template = await client.post(
        "/api/v1/consents/templates",
        json={
            "name": f"Consent {uuid.uuid4()}",
            "body_markdown": "Consiento el tratamiento.",
            "questions": [],
        },
        headers=headers,
    )
    assert template.status_code == 201, template.text
    version_id = template.json()["latest_version"]["id"]
    template_id = template.json()["id"]
    publish = await client.post(
        f"/api/v1/consents/templates/{template_id}/versions/{version_id}/publish",
        headers=headers,
    )
    assert publish.status_code == 200, publish.text
    return version_id


async def _create_request(client, headers: dict, patient_id: str, version_id: str) -> dict:
    response = await client.post(
        f"/api/v1/consents/requests?patient_id={patient_id}&template_version_id={version_id}",
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _setup(client) -> dict:
    org = await _register_org(client)
    headers = {"Authorization": f"Bearer {org['access_token']}"}
    patient_id = await _create_patient(client, headers)
    version_id = await _published_template_version(client, headers)
    return {
        "headers": headers,
        "organization_id": org["organization_id"],
        "patient_id": patient_id,
        "version_id": version_id,
    }


async def test_invalidate_requires_pending_status(client):
    ctx = await _setup(client)
    request = await _create_request(client, ctx["headers"], ctx["patient_id"], ctx["version_id"])

    invalidated = await client.post(
        f"/api/v1/consents/requests/{request['consent_request_id']}/invalidate",
        json={"reason": "Patient requested it be cancelled"},
        headers=ctx["headers"],
    )
    assert invalidated.status_code == 200, invalidated.text
    assert invalidated.json()["status"] == "invalidated"

    # Already invalidated — a second invalidate must be rejected, not
    # silently re-applied.
    second_attempt = await client.post(
        f"/api/v1/consents/requests/{request['consent_request_id']}/invalidate",
        json={"reason": "Trying again"},
        headers=ctx["headers"],
    )
    assert second_attempt.status_code == 409


async def test_invalidate_is_org_scoped(client):
    ctx = await _setup(client)
    request = await _create_request(client, ctx["headers"], ctx["patient_id"], ctx["version_id"])

    other_org = await _register_org(client)
    other_headers = {"Authorization": f"Bearer {other_org['access_token']}"}

    cross_org = await client.post(
        f"/api/v1/consents/requests/{request['consent_request_id']}/invalidate",
        json={"reason": "Should not be allowed"},
        headers=other_headers,
    )
    assert cross_org.status_code == 404


async def test_invalidated_link_returns_structured_reason_to_patient(client):
    ctx = await _setup(client)
    request = await _create_request(client, ctx["headers"], ctx["patient_id"], ctx["version_id"])
    await client.post(
        f"/api/v1/consents/requests/{request['consent_request_id']}/invalidate",
        json={"reason": "No longer needed"},
        headers=ctx["headers"],
    )

    form = await client.get(f"/api/v1/public/consents/{request['token']}")
    assert form.status_code == 410
    assert form.json()["detail"]["reason"] == "invalidated"
    # The staff-entered reason is not leaked to the patient-facing endpoint.
    assert "No longer needed" not in form.text


async def test_unknown_token_returns_not_found_reason(client):
    form = await client.get("/api/v1/public/consents/does-not-exist")
    assert form.status_code == 404
    assert form.json()["detail"]["reason"] == "not_found"


async def test_resend_supersedes_pending_and_reuses_expired(client):
    ctx = await _setup(client)
    pending_request = await _create_request(
        client, ctx["headers"], ctx["patient_id"], ctx["version_id"]
    )

    resent = await client.post(
        f"/api/v1/consents/requests/{pending_request['consent_request_id']}/resend",
        headers=ctx["headers"],
    )
    assert resent.status_code == 201, resent.text
    new_token = resent.json()["token"]
    assert new_token != pending_request["token"]

    # The original is now invalidated (superseded), so its link 410s...
    original_form = await client.get(f"/api/v1/public/consents/{pending_request['token']}")
    assert original_form.status_code == 410
    assert original_form.json()["detail"]["reason"] == "invalidated"

    # ...while the new link is live.
    new_form = await client.get(f"/api/v1/public/consents/{new_token}")
    assert new_form.status_code == 200


async def test_resend_rejects_completed_or_invalidated_requests(client):
    ctx = await _setup(client)
    request = await _create_request(client, ctx["headers"], ctx["patient_id"], ctx["version_id"])
    await client.post(
        f"/api/v1/consents/requests/{request['consent_request_id']}/invalidate",
        json={"reason": "Cancelled"},
        headers=ctx["headers"],
    )

    resend_after_invalidate = await client.post(
        f"/api/v1/consents/requests/{request['consent_request_id']}/resend",
        headers=ctx["headers"],
    )
    assert resend_after_invalidate.status_code == 409


async def test_lifecycle_mutations_are_audited(client):
    ctx = await _setup(client)
    request = await _create_request(client, ctx["headers"], ctx["patient_id"], ctx["version_id"])
    await client.post(
        f"/api/v1/consents/requests/{request['consent_request_id']}/invalidate",
        json={"reason": "Testing audit coverage"},
        headers=ctx["headers"],
    )

    audit_events = await client.get("/api/v1/audit", headers=ctx["headers"])
    assert audit_events.status_code == 200
    invalidated_event = next(
        e for e in audit_events.json() if e["action"] == "consent_request.invalidated"
    )
    assert invalidated_event["resource_id"] == request["consent_request_id"]
    assert invalidated_event["actor_user_id"] is not None
