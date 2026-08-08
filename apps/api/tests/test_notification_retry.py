"""Coverage for the "Resend or escalate when delivery fails" gap under
"Consent delivery automation" in missing_features.md: a permanently-failed
WhatsApp send previously had no recovery path beyond a staff member noticing
the red badge on the notifications page. Same real-database-plus-savepoint
pattern as test_consent_lifecycle.py — see that module's docstring for the
full rationale.
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
from medical_api.modules.notifications.models import (
    NotificationChannel,
    NotificationMessage,
    NotificationStatus,
    OutboxEvent,
)

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
        pytest.skip("no reachable database for notification-retry tests")


async def _register_org(client) -> dict:
    response = await client.post(
        "/api/v1/auth/register-organization",
        json={
            "organization_name": f"Retry Clinic {uuid.uuid4()}",
            "admin_email": f"retry-{uuid.uuid4()}@example.com",
            "admin_password": "supersecret123",
            "admin_full_name": "Retry Admin",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _seed_message(
    session, organization_id: uuid.UUID, *, status: NotificationStatus, template_key: str
) -> NotificationMessage:
    message = NotificationMessage(
        organization_id=organization_id,
        channel=NotificationChannel.WHATSAPP,
        status=status,
        recipient="+573001112233",
        template_key=template_key,
        payload={"appointment_id": str(uuid.uuid4())},
        failure_reason="WHATSAPP_API_TOKEN / WHATSAPP_PHONE_NUMBER_ID are not configured."
        if status == NotificationStatus.FAILED
        else None,
    )
    session.add(message)
    await session.flush()
    return message


async def test_retry_requires_designated_role_and_is_org_scoped(client):
    org = await _register_org(client)
    headers = {"Authorization": f"Bearer {org['access_token']}"}
    message = await _seed_message(
        client.db_session,
        uuid.UUID(org["organization_id"]),
        status=NotificationStatus.FAILED,
        template_key="appointment_confirmation",
    )

    other_org = await _register_org(client)
    other_headers = {"Authorization": f"Bearer {other_org['access_token']}"}
    cross_org = await client.post(
        f"/api/v1/notifications/{message.id}/retry", headers=other_headers
    )
    assert cross_org.status_code == 404

    auditor = await client.post(
        "/api/v1/auth/invites",
        json={"email": f"aud-{uuid.uuid4()}@example.com", "role": "auditor"},
        headers=headers,
    )
    assert auditor.status_code == 201, auditor.text
    accept = await client.post(
        f"/api/v1/auth/invites/{auditor.json()['token']}/accept",
        json={"full_name": "Auditor", "password": "supersecret123"},
    )
    assert accept.status_code == 201, accept.text
    auditor_headers = {"Authorization": f"Bearer {accept.json()['access_token']}"}
    forbidden = await client.post(
        f"/api/v1/notifications/{message.id}/retry", headers=auditor_headers
    )
    assert forbidden.status_code == 403


async def test_retry_requires_failed_status(client):
    org = await _register_org(client)
    headers = {"Authorization": f"Bearer {org['access_token']}"}
    message = await _seed_message(
        client.db_session,
        uuid.UUID(org["organization_id"]),
        status=NotificationStatus.SENT,
        template_key="appointment_confirmation",
    )

    response = await client.post(f"/api/v1/notifications/{message.id}/retry", headers=headers)
    assert response.status_code == 409, response.text


async def test_retry_rejects_unsupported_template_key(client):
    org = await _register_org(client)
    headers = {"Authorization": f"Bearer {org['access_token']}"}
    message = await _seed_message(
        client.db_session,
        uuid.UUID(org["organization_id"]),
        status=NotificationStatus.FAILED,
        template_key="consent_link",
    )

    response = await client.post(f"/api/v1/notifications/{message.id}/retry", headers=headers)
    assert response.status_code == 409, response.text


async def test_retry_succeeds_enqueues_event_and_is_audited(client):
    org = await _register_org(client)
    headers = {"Authorization": f"Bearer {org['access_token']}"}
    message = await _seed_message(
        client.db_session,
        uuid.UUID(org["organization_id"]),
        status=NotificationStatus.FAILED,
        template_key="appointment_confirmation",
    )

    response = await client.post(f"/api/v1/notifications/{message.id}/retry", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "pending"
    assert response.json()["failure_reason"] is None

    outbox_stmt = select(OutboxEvent).where(
        OutboxEvent.organization_id == uuid.UUID(org["organization_id"]),
        OutboxEvent.event_type == "notification.retry_requested",
    )
    events = (await client.db_session.execute(outbox_stmt)).scalars().all()
    assert len(events) == 1
    assert events[0].payload == {"notification_message_id": str(message.id)}

    audit_events = await client.get("/api/v1/audit", headers=headers)
    assert audit_events.status_code == 200
    retried_event = next(
        e for e in audit_events.json() if e["action"] == "notification.retry_requested"
    )
    assert retried_event["resource_id"] == str(message.id)
