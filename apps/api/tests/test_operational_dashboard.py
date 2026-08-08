"""HTTP-to-PostgreSQL coverage for the operational dashboard data sources."""

import hashlib
import uuid
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from medical_api.core.config import get_settings
from medical_api.core.database import engine, get_db
from medical_api.main import app
from medical_api.modules.consents.models import (
    ConsentRequest,
    ConsentRequestStatus,
    ConsentSubmission,
    ConsentTemplate,
    ConsentTemplateVersion,
    EligibilityResult,
)
from medical_api.modules.notifications.models import (
    NotificationChannel,
    NotificationMessage,
    NotificationStatus,
)
from medical_api.modules.patients.models import Patient
from medical_api.modules.scheduling.models import Appointment, AppointmentStatus, Practitioner

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
        pytest.skip("no reachable database for operational-dashboard integration tests")


async def _register_org(client) -> tuple[dict[str, str], dict]:
    response = await client.post(
        "/api/v1/auth/register-organization",
        json={
            "organization_name": f"Dashboard Clinic {uuid.uuid4()}",
            "admin_email": f"dashboard-{uuid.uuid4()}@example.com",
            "admin_password": "supersecret123",
            "admin_full_name": "Dashboard Admin",
        },
    )
    assert response.status_code == 201, response.text
    token_payload = response.json()
    headers = {"Authorization": f"Bearer {token_payload['access_token']}"}
    me = await client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200, me.text
    return headers, me.json()


async def test_dashboard_sources_filter_and_preserve_organization_boundaries(client):
    org_a_headers, org_a_user = await _register_org(client)
    org_b_headers, _ = await _register_org(client)
    session = client.db_session
    organization_id = uuid.UUID(org_a_user["organization_id"])
    now = datetime.now(UTC)

    patient = Patient(
        organization_id=organization_id,
        first_name="Ana",
        last_name="Dashboard",
        document_id=f"dashboard-{uuid.uuid4()}",
        date_of_birth=None,
        phone_number="+573001112233",
        email=None,
    )
    practitioner = Practitioner(
        organization_id=organization_id,
        user_id=uuid.UUID(org_a_user["id"]),
        specialty="Medicina estética",
    )
    template = ConsentTemplate(organization_id=organization_id, name="Dashboard consent")
    session.add_all([patient, practitioner, template])
    await session.flush()

    template_version = ConsentTemplateVersion(
        template_id=template.id,
        version_number=1,
        published_at=now,
        body_markdown="Consentimiento de prueba",
    )
    session.add(template_version)
    await session.flush()

    appointments = [
        Appointment(
            organization_id=organization_id,
            patient_id=patient.id,
            practitioner_id=practitioner.id,
            room_id=None,
            treatment_definition_id=None,
            starts_at=now + timedelta(hours=2),
            ends_at=now + timedelta(hours=3),
            status=AppointmentStatus.CONFIRMED,
            notes=None,
        ),
        Appointment(
            organization_id=organization_id,
            patient_id=patient.id,
            practitioner_id=practitioner.id,
            room_id=None,
            treatment_definition_id=None,
            starts_at=now + timedelta(days=1),
            ends_at=now + timedelta(days=1, hours=1),
            status=AppointmentStatus.CANCELLED,
            notes=None,
        ),
    ]
    pending_request = ConsentRequest(
        organization_id=organization_id,
        patient_id=patient.id,
        appointment_id=None,
        template_version_id=template_version.id,
        token_hash=hashlib.sha256(uuid.uuid4().bytes).hexdigest(),
        status=ConsentRequestStatus.PENDING,
        expires_at=now + timedelta(hours=24),
    )
    expired_request = ConsentRequest(
        organization_id=organization_id,
        patient_id=patient.id,
        appointment_id=None,
        template_version_id=template_version.id,
        token_hash=hashlib.sha256(uuid.uuid4().bytes).hexdigest(),
        status=ConsentRequestStatus.EXPIRED,
        expires_at=now - timedelta(hours=1),
    )
    review_request = ConsentRequest(
        organization_id=organization_id,
        patient_id=patient.id,
        appointment_id=None,
        template_version_id=template_version.id,
        token_hash=hashlib.sha256(uuid.uuid4().bytes).hexdigest(),
        status=ConsentRequestStatus.COMPLETED,
        expires_at=now + timedelta(hours=24),
    )
    failed_notification = NotificationMessage(
        organization_id=organization_id,
        channel=NotificationChannel.WHATSAPP,
        status=NotificationStatus.FAILED,
        recipient="+573001112233",
        template_key="appointment_confirmation",
        payload={},
        provider_message_id=None,
        related_outbox_event_id=None,
        sent_at=None,
        delivered_at=None,
        failure_reason="Proveedor no disponible",
    )
    session.add_all(
        [
            *appointments,
            pending_request,
            expired_request,
            review_request,
            failed_notification,
        ]
    )
    await session.flush()
    session.add(
        ConsentSubmission(
            consent_request_id=review_request.id,
            timezone="America/Bogota",
            ip_address="127.0.0.1",
            user_agent="pytest",
            eligibility_result=EligibilityResult.REQUIRES_MANUAL_REVIEW,
        )
    )
    await session.commit()

    appointment_params = {
        "start": (now - timedelta(hours=1)).isoformat(),
        "end": (now + timedelta(days=2)).isoformat(),
    }
    org_a_appointments = await client.get(
        "/api/v1/appointments", params=appointment_params, headers=org_a_headers
    )
    assert org_a_appointments.status_code == 200, org_a_appointments.text
    assert {item["status"] for item in org_a_appointments.json()} == {"confirmed", "cancelled"}

    pending = await client.get(
        "/api/v1/consents/requests", params={"status": "pending"}, headers=org_a_headers
    )
    assert pending.status_code == 200, pending.text
    assert [item["id"] for item in pending.json()] == [str(pending_request.id)]

    expired = await client.get(
        "/api/v1/consents/requests", params={"status": "expired"}, headers=org_a_headers
    )
    assert expired.status_code == 200, expired.text
    assert [item["id"] for item in expired.json()] == [str(expired_request.id)]

    needs_review = await client.get(
        "/api/v1/consents/requests", params={"needs_review": "true"}, headers=org_a_headers
    )
    assert needs_review.status_code == 200, needs_review.text
    assert [item["id"] for item in needs_review.json()] == [str(review_request.id)]

    org_a_notifications = await client.get("/api/v1/notifications", headers=org_a_headers)
    assert org_a_notifications.status_code == 200, org_a_notifications.text
    assert len(org_a_notifications.json()) == 1
    assert org_a_notifications.json()[0]["failure_reason"] == "Proveedor no disponible"
    assert org_a_notifications.json()[0]["created_at"] is not None

    org_b_appointments = await client.get(
        "/api/v1/appointments", params=appointment_params, headers=org_b_headers
    )
    org_b_pending = await client.get(
        "/api/v1/consents/requests", params={"status": "pending"}, headers=org_b_headers
    )
    org_b_review = await client.get(
        "/api/v1/consents/requests", params={"needs_review": "true"}, headers=org_b_headers
    )
    org_b_notifications = await client.get("/api/v1/notifications", headers=org_b_headers)
    assert org_b_appointments.json() == []
    assert org_b_pending.json() == []
    assert org_b_review.json() == []
    assert org_b_notifications.json() == []
