"""Real-PostgreSQL coverage for WhatsApp opt-out and send suppression."""

import hashlib
import hmac
import json
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import ClassVar

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
from medical_api.modules.notifications import webhook_router
from medical_api.modules.notifications.models import (
    NotificationCategory,
    NotificationChannel,
    NotificationMessage,
    NotificationStatus,
)
from medical_api.modules.organizations.models import Organization
from medical_api.modules.organizations.repository import OrganizationRepository
from medical_api.modules.patients.models import Patient
from medical_worker.activities import send_whatsapp

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
        pytest.skip("no reachable database for communication-preference integration tests")


async def _register_org(client) -> tuple[dict[str, str], dict]:
    response = await client.post(
        "/api/v1/auth/register-organization",
        json={
            "organization_name": f"Preferences Clinic {uuid.uuid4()}",
            "admin_email": f"preferences-{uuid.uuid4()}@example.com",
            "admin_password": "supersecret123",
            "admin_full_name": "Preferences Admin",
        },
    )
    assert response.status_code == 201, response.text
    token_payload = response.json()
    headers = {"Authorization": f"Bearer {token_payload['access_token']}"}
    me = await client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200, me.text
    return headers, me.json()


async def _create_direct_patient(
    session: AsyncSession,
    organization_id: uuid.UUID,
    *,
    phone_number: str,
    opted_out: bool,
) -> Patient:
    patient = Patient(
        organization_id=organization_id,
        first_name="WhatsApp",
        last_name="Patient",
        document_id=f"preference-{uuid.uuid4()}",
        date_of_birth=None,
        phone_number=phone_number,
        email=None,
        whatsapp_opt_in_at=datetime.now(UTC),
        whatsapp_opt_out=opted_out,
        whatsapp_opt_out_at=datetime.now(UTC) if opted_out else None,
    )
    session.add(patient)
    await session.flush()
    return patient


def _signed_payload(payload: dict, secret: str) -> tuple[bytes, str]:
    raw_body = json.dumps(payload, separators=(",", ":")).encode()
    digest = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return raw_body, f"sha256={digest}"


async def test_whatsapp_keyword_opts_patient_out_and_records_audit(client, monkeypatch):
    session = client.db_session
    organization = await OrganizationRepository(session).get_first()
    if organization is None:
        organization = Organization(name=f"Webhook Clinic {uuid.uuid4()}")
        session.add(organization)
        await session.flush()
    patient = await _create_direct_patient(
        session,
        organization.id,
        phone_number="+57 300 111 2233",
        opted_out=False,
    )
    await session.commit()

    app_secret = "communication-preferences-test-secret"
    monkeypatch.setattr(webhook_router.settings, "whatsapp_app_secret", app_secret)
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "waba-id",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messages": [
                                {
                                    "from": "573001112233",
                                    "id": "wamid.opt-out",
                                    "type": "text",
                                    "text": {"body": "No molestar, por favor"},
                                }
                            ]
                        },
                    }
                ],
            }
        ],
    }
    raw_body, signature = _signed_payload(payload, app_secret)
    response = await client.post(
        "/api/v1/webhooks/whatsapp",
        content=raw_body,
        headers={
            "content-type": "application/json",
            "x-hub-signature-256": signature,
            "user-agent": "Meta-Test-Agent",
        },
    )
    assert response.status_code == 200, response.text

    await session.refresh(patient)
    assert patient.whatsapp_opt_out is True
    assert patient.whatsapp_opt_out_at is not None
    event = (
        await session.execute(
            select(AuditEvent).where(
                AuditEvent.action == "patient.whatsapp_opt_out",
                AuditEvent.resource_id == str(patient.id),
            )
        )
    ).scalar_one()
    assert event.actor_user_id is None
    assert event.user_agent == "Meta-Test-Agent"
    assert event.event_metadata["provider_message_id"] == "wamid.opt-out"


async def test_staff_toggle_is_org_scoped_and_audited_and_phone_records_opt_in(client):
    org_a_headers, org_a_user = await _register_org(client)
    org_b_headers, _ = await _register_org(client)

    created = await client.post(
        "/api/v1/patients",
        json={
            "first_name": "Laura",
            "last_name": "Gómez",
            "document_id": f"pref-{uuid.uuid4().hex}",
            "phone_number": "+573009998877",
        },
        headers=org_a_headers,
    )
    assert created.status_code == 201, created.text
    assert created.json()["whatsapp_opt_in_at"] is not None
    patient_id = created.json()["id"]
    path = f"/api/v1/patients/{patient_id}/communication-preferences"

    cross_org_read = await client.get(path, headers=org_b_headers)
    cross_org_update = await client.patch(
        path, json={"whatsapp_opt_out": True}, headers=org_b_headers
    )
    assert cross_org_read.status_code == 404
    assert cross_org_update.status_code == 404

    updated = await client.patch(path, json={"whatsapp_opt_out": True}, headers=org_a_headers)
    assert updated.status_code == 200, updated.text
    assert updated.json()["whatsapp_opt_out"] is True
    assert updated.json()["whatsapp_opt_out_at"] is not None

    event = (
        await client.db_session.execute(
            select(AuditEvent).where(
                AuditEvent.action == "patient.whatsapp_opt_out.updated",
                AuditEvent.resource_id == patient_id,
            )
        )
    ).scalar_one()
    assert event.actor_user_id == uuid.UUID(org_a_user["id"])
    assert event.event_metadata == {"previous_value": False, "whatsapp_opt_out": True}


class FakeWhatsAppClient:
    calls: ClassVar[list[tuple[str, str, list[str]]]] = []

    async def send_template_message(self, to: str, template_name: str, params: list[str]) -> str:
        self.calls.append((to, template_name, params))
        return "wamid.preference-test"


def _use_test_session(monkeypatch, session: AsyncSession) -> None:
    @asynccontextmanager
    async def session_factory():
        yield session

    FakeWhatsAppClient.calls = []
    monkeypatch.setattr(send_whatsapp, "async_session_factory", session_factory)
    monkeypatch.setattr(send_whatsapp, "WhatsAppClient", FakeWhatsAppClient)


async def _create_notification(
    session: AsyncSession, patient: Patient, category: NotificationCategory
) -> NotificationMessage:
    message = NotificationMessage(
        organization_id=patient.organization_id,
        channel=NotificationChannel.WHATSAPP,
        category=category,
        recipient=patient.phone_number,
        template_key="preference_test",
        payload={"patient_id": str(patient.id)},
        provider_message_id=None,
        related_outbox_event_id=None,
        sent_at=None,
        delivered_at=None,
        failure_reason=None,
    )
    session.add(message)
    await session.commit()
    return message


async def test_marketing_send_is_suppressed_after_opt_out(client, monkeypatch):
    session = client.db_session
    organization = Organization(name=f"Marketing Clinic {uuid.uuid4()}")
    session.add(organization)
    await session.flush()
    patient = await _create_direct_patient(
        session, organization.id, phone_number="+573101234567", opted_out=True
    )
    message = await _create_notification(session, patient, NotificationCategory.MARKETING)
    _use_test_session(monkeypatch, session)

    await send_whatsapp._send(
        patient.phone_number, "marketing_offer", [patient.first_name], str(message.id)
    )

    await session.refresh(message)
    assert message.status == NotificationStatus.SUPPRESSED
    assert FakeWhatsAppClient.calls == []


async def test_transactional_send_is_not_suppressed_after_opt_out(client, monkeypatch):
    session = client.db_session
    organization = Organization(name=f"Transactional Clinic {uuid.uuid4()}")
    session.add(organization)
    await session.flush()
    patient = await _create_direct_patient(
        session, organization.id, phone_number="+573109876543", opted_out=True
    )
    message = await _create_notification(session, patient, NotificationCategory.TRANSACTIONAL)
    _use_test_session(monkeypatch, session)

    await send_whatsapp._send(
        patient.phone_number, "appointment_confirmation", [patient.first_name], str(message.id)
    )

    await session.refresh(message)
    assert message.status == NotificationStatus.SENT
    assert message.provider_message_id == "wamid.preference-test"
    assert len(FakeWhatsAppClient.calls) == 1
