"""Coverage for `PATCH /api/v1/appointments/{id}/reschedule` — see
"Appointment management" in missing_features.md ("Edit/reschedule an
existing appointment"). Before this endpoint existed, a booked appointment
could only have its status changed, never moved to a different time; the
new endpoint reuses the same availability/conflict checks `schedule()`
already enforces, excluding the appointment being moved from its own
conflict check. Same real-database-plus-savepoint pattern as
test_appointment_scheduling_validation.py — see that module's docstring
for the full rationale.
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
_WINDOW_START = datetime.combine(_NEXT_MONDAY, datetime.min.time(), tzinfo=UTC) + timedelta(hours=9)


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
        pytest.skip("no reachable database for appointment-reschedule tests")


async def _register_org(client) -> dict:
    response = await client.post(
        "/api/v1/auth/register-organization",
        json={
            "organization_name": f"Reschedule Clinic {uuid.uuid4()}",
            "admin_email": f"reschedule-{uuid.uuid4()}@example.com",
            "admin_password": "supersecret123",
            "admin_full_name": "Reschedule Admin",
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
    me = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {accept.json()['access_token']}"}
    )
    assert me.status_code == 200, me.text

    practitioner = await client.post(
        "/api/v1/practitioners",
        json={"user_id": me.json()["id"], "specialty": "Dermatología"},
        headers=headers,
    )
    assert practitioner.status_code == 201, practitioner.text
    return practitioner.json()["id"]


async def _add_availability_rule(client, headers: dict, practitioner_id: str, weekday: int) -> None:
    response = await client.post(
        "/api/v1/appointments/availability-rules",
        json={
            "practitioner_id": practitioner_id,
            "weekday": weekday,
            "start_time": "09:00:00",
            "end_time": "17:00:00",
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text


async def _setup(client) -> dict:
    org = await _register_org(client)
    headers = {"Authorization": f"Bearer {org['access_token']}"}
    patient_id = await _create_patient(client, headers)
    practitioner_id = await _create_practitioner(client, headers)
    await _add_availability_rule(client, headers, practitioner_id, _NEXT_MONDAY.weekday())
    return {
        "headers": headers,
        "organization_id": org["organization_id"],
        "patient_id": patient_id,
        "practitioner_id": practitioner_id,
    }


async def _book(client, ctx: dict, starts_at: datetime) -> dict:
    response = await client.post(
        "/api/v1/appointments",
        json={
            "patient_id": ctx["patient_id"],
            "practitioner_id": ctx["practitioner_id"],
            "starts_at": starts_at.isoformat(),
            "ends_at": (starts_at + timedelta(minutes=30)).isoformat(),
        },
        headers=ctx["headers"],
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_reschedule_to_another_in_window_slot_succeeds(client):
    ctx = await _setup(client)
    appointment = await _book(client, ctx, _WINDOW_START)
    new_start = _WINDOW_START + timedelta(hours=2)

    response = await client.patch(
        f"/api/v1/appointments/{appointment['id']}/reschedule",
        json={
            "starts_at": new_start.isoformat(),
            "ends_at": (new_start + timedelta(minutes=30)).isoformat(),
        },
        headers=ctx["headers"],
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert datetime.fromisoformat(body["starts_at"]) == new_start

    history = await client.get(
        f"/api/v1/appointments/{appointment['id']}/status-history", headers=ctx["headers"]
    )
    assert history.status_code == 200, history.text
    # Reschedule moves the time, not the status — no new history entry.
    assert len(history.json()) == 1


async def test_reschedule_outside_availability_is_rejected(client):
    ctx = await _setup(client)
    appointment = await _book(client, ctx, _WINDOW_START)
    outside_start = datetime.combine(_NEXT_MONDAY, datetime.min.time(), tzinfo=UTC) + timedelta(
        hours=3
    )

    response = await client.patch(
        f"/api/v1/appointments/{appointment['id']}/reschedule",
        json={
            "starts_at": outside_start.isoformat(),
            "ends_at": (outside_start + timedelta(minutes=30)).isoformat(),
        },
        headers=ctx["headers"],
    )
    assert response.status_code == 409, response.text


async def test_reschedule_onto_another_appointment_is_rejected(client):
    ctx = await _setup(client)
    first = await _book(client, ctx, _WINDOW_START)
    second_start = _WINDOW_START + timedelta(hours=2)
    await _book(client, ctx, second_start)

    response = await client.patch(
        f"/api/v1/appointments/{first['id']}/reschedule",
        json={
            "starts_at": second_start.isoformat(),
            "ends_at": (second_start + timedelta(minutes=30)).isoformat(),
        },
        headers=ctx["headers"],
    )
    assert response.status_code == 409, response.text


async def test_reschedule_to_the_same_slot_it_already_occupies_succeeds(client):
    # Regression guard for the exclude_appointment_id plumbing: without it,
    # an appointment would appear to conflict with itself and a no-op
    # reschedule (or a small notes-only edit reusing this endpoint) would
    # always 409.
    ctx = await _setup(client)
    appointment = await _book(client, ctx, _WINDOW_START)

    response = await client.patch(
        f"/api/v1/appointments/{appointment['id']}/reschedule",
        json={
            "starts_at": appointment["starts_at"],
            "ends_at": appointment["ends_at"],
        },
        headers=ctx["headers"],
    )
    assert response.status_code == 200, response.text


async def test_reschedule_a_cancelled_appointment_is_rejected(client):
    ctx = await _setup(client)
    appointment = await _book(client, ctx, _WINDOW_START)
    cancel = await client.post(
        f"/api/v1/appointments/{appointment['id']}/status",
        json={"status": "cancelled"},
        headers=ctx["headers"],
    )
    assert cancel.status_code == 200, cancel.text

    new_start = _WINDOW_START + timedelta(hours=2)
    response = await client.patch(
        f"/api/v1/appointments/{appointment['id']}/reschedule",
        json={
            "starts_at": new_start.isoformat(),
            "ends_at": (new_start + timedelta(minutes=30)).isoformat(),
        },
        headers=ctx["headers"],
    )
    assert response.status_code == 409, response.text


async def test_reschedule_an_appointment_from_another_org_is_rejected(client):
    ctx = await _setup(client)
    other_ctx = await _setup(client)
    appointment = await _book(client, other_ctx, _WINDOW_START)

    new_start = _WINDOW_START + timedelta(hours=2)
    response = await client.patch(
        f"/api/v1/appointments/{appointment['id']}/reschedule",
        json={
            "starts_at": new_start.isoformat(),
            "ends_at": (new_start + timedelta(minutes=30)).isoformat(),
        },
        headers=ctx["headers"],
    )
    assert response.status_code == 404, response.text


async def test_reschedule_records_an_audit_entry_with_old_and_new_times(client):
    ctx = await _setup(client)
    appointment = await _book(client, ctx, _WINDOW_START)
    new_start = _WINDOW_START + timedelta(hours=2)

    response = await client.patch(
        f"/api/v1/appointments/{appointment['id']}/reschedule",
        json={
            "starts_at": new_start.isoformat(),
            "ends_at": (new_start + timedelta(minutes=30)).isoformat(),
        },
        headers=ctx["headers"],
    )
    assert response.status_code == 200, response.text

    result = await client.db_session.execute(
        text(
            "SELECT event_metadata FROM audit_events WHERE action = 'appointment.rescheduled' "
            "AND resource_id = :resource_id"
        ),
        {"resource_id": appointment["id"]},
    )
    row = result.first()
    assert row is not None
    metadata = row[0]
    assert datetime.fromisoformat(metadata["previous_starts_at"]) == datetime.fromisoformat(
        appointment["starts_at"]
    )
    assert datetime.fromisoformat(metadata["starts_at"]) == new_start
