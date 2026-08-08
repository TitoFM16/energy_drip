"""Coverage for "Display appointment status history" under "Appointment
management" in missing_features.md: `AppointmentStatusHistory` was already
recorded on every schedule/status-change, but had no read endpoint at all,
and `changed_by_user_id` was never actually populated despite the column
existing for exactly that purpose. Same real-database-plus-savepoint
pattern as test_appointment_scheduling_validation.py — see that module's
docstring for the full rationale.
"""

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

pytestmark = pytest.mark.asyncio(loop_scope="session")

_NEXT_MONDAY = datetime.now(UTC).date() + timedelta(
    days=(7 - datetime.now(UTC).date().weekday()) % 7 or 7
)
_IN_WINDOW_START = datetime.combine(_NEXT_MONDAY, datetime.min.time(), tzinfo=UTC) + timedelta(
    hours=9
)


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
        pytest.skip("no reachable database for appointment-status-history tests")


async def _register_org(client) -> dict:
    response = await client.post(
        "/api/v1/auth/register-organization",
        json={
            "organization_name": f"History Clinic {uuid.uuid4()}",
            "admin_email": f"history-{uuid.uuid4()}@example.com",
            "admin_password": "supersecret123",
            "admin_full_name": "History Admin",
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


async def _create_practitioner(client, headers: dict) -> str:
    invite = await client.post(
        "/api/v1/auth/invites",
        json={"email": f"practitioner-{uuid.uuid4()}@example.com", "role": "practitioner"},
        headers=headers,
    )
    assert invite.status_code == 201, invite.text
    accept = await client.post(
        f"/api/v1/auth/invites/{invite.json()['token']}/accept",
        json={"full_name": "Practitioner", "password": "supersecret123"},
    )
    assert accept.status_code == 201, accept.text

    practitioner = await client.post(
        "/api/v1/practitioners",
        json={
            "user_id": (
                await client.get(
                    "/api/v1/auth/me",
                    headers={"Authorization": f"Bearer {accept.json()['access_token']}"},
                )
            ).json()["id"],
            "specialty": "Dermatología",
        },
        headers=headers,
    )
    assert practitioner.status_code == 201, practitioner.text
    return practitioner.json()["id"]


async def _setup(client) -> dict:
    org = await _register_org(client)
    headers = {"Authorization": f"Bearer {org['access_token']}"}
    patient_id = await _create_patient(client, headers)
    practitioner_id = await _create_practitioner(client, headers)
    rule = await client.post(
        "/api/v1/appointments/availability-rules",
        json={
            "practitioner_id": practitioner_id,
            "weekday": _NEXT_MONDAY.weekday(),
            "start_time": "09:00:00",
            "end_time": "17:00:00",
        },
        headers=headers,
    )
    assert rule.status_code == 201, rule.text
    return {
        "headers": headers,
        "organization_id": org["organization_id"],
        "patient_id": patient_id,
        "practitioner_id": practitioner_id,
    }


async def test_status_history_records_creation_and_transitions_with_actor(client):
    ctx = await _setup(client)
    appointment = await client.post(
        "/api/v1/appointments",
        json={
            "patient_id": ctx["patient_id"],
            "practitioner_id": ctx["practitioner_id"],
            "starts_at": _IN_WINDOW_START.isoformat(),
            "ends_at": (_IN_WINDOW_START + timedelta(minutes=30)).isoformat(),
        },
        headers=ctx["headers"],
    )
    assert appointment.status_code == 201, appointment.text
    appointment_id = appointment.json()["id"]

    status_change = await client.post(
        f"/api/v1/appointments/{appointment_id}/status",
        json={"status": "confirmed", "reason": "Paciente confirmó por WhatsApp"},
        headers=ctx["headers"],
    )
    assert status_change.status_code == 200, status_change.text

    history = await client.get(
        f"/api/v1/appointments/{appointment_id}/status-history", headers=ctx["headers"]
    )
    assert history.status_code == 200, history.text
    entries = history.json()
    assert len(entries) == 2

    assert entries[0]["from_status"] is None
    assert entries[0]["to_status"] == "scheduled"
    assert entries[0]["changed_by_user_id"] is not None
    assert entries[0]["changed_by_full_name"] == "History Admin"

    assert entries[1]["from_status"] == "scheduled"
    assert entries[1]["to_status"] == "confirmed"
    assert entries[1]["reason"] == "Paciente confirmó por WhatsApp"
    assert entries[1]["changed_by_full_name"] == "History Admin"


async def test_status_history_is_org_scoped(client):
    ctx = await _setup(client)
    appointment = await client.post(
        "/api/v1/appointments",
        json={
            "patient_id": ctx["patient_id"],
            "practitioner_id": ctx["practitioner_id"],
            "starts_at": _IN_WINDOW_START.isoformat(),
            "ends_at": (_IN_WINDOW_START + timedelta(minutes=30)).isoformat(),
        },
        headers=ctx["headers"],
    )
    assert appointment.status_code == 201, appointment.text
    appointment_id = appointment.json()["id"]

    other_org = await _register_org(client)
    other_headers = {"Authorization": f"Bearer {other_org['access_token']}"}
    cross_org = await client.get(
        f"/api/v1/appointments/{appointment_id}/status-history", headers=other_headers
    )
    assert cross_org.status_code == 404


async def test_status_history_404s_for_unknown_appointment(client):
    ctx = await _setup(client)
    response = await client.get(
        f"/api/v1/appointments/{uuid.uuid4()}/status-history", headers=ctx["headers"]
    )
    assert response.status_code == 404
