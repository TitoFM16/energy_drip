"""Coverage for the "Appointment management" trust-boundary gaps in
missing_features.md: the raw `POST /api/v1/appointments` endpoint never
validated that patient_id/practitioner_id/room_id actually belong to the
caller's organization, never enforced that the requested time falls inside
the practitioner's configured availability, and never rejected a room
double-booking the way it already rejected a practitioner double-booking.
Also covers the `duration_minutes` bound on `GET /appointments/availability`
— a duration <= 0 used to hang AvailabilityService.compute_slots' slot-walk
loop forever (it never advances past a day's end). Same
real-database-plus-savepoint pattern as test_consent_lifecycle.py — see that
module's docstring for the full rationale.
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
from medical_api.modules.scheduling.models import Location, Room

pytestmark = pytest.mark.asyncio(loop_scope="session")

# A future Monday at 09:00 UTC — inside the 09:00-17:00 Monday rule every
# `_setup` clinic below gets, and far enough out that "no past slots"
# filtering elsewhere in the module never interferes.
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
        pytest.skip("no reachable database for appointment-scheduling-validation tests")


async def _register_org(client) -> dict:
    response = await client.post(
        "/api/v1/auth/register-organization",
        json={
            "organization_name": f"Scheduling Clinic {uuid.uuid4()}",
            "admin_email": f"scheduling-{uuid.uuid4()}@example.com",
            "admin_password": "supersecret123",
            "admin_full_name": "Scheduling Admin",
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


async def _create_room(session, organization_id: uuid.UUID) -> Room:
    # No API/UI can create a room yet (see RoomRepository's docstring) — a
    # direct model insert is the only way to get one, same as
    # test_documents.py's `_seed_document` helper does for its own
    # not-yet-API-reachable setup state.
    location = Location(organization_id=organization_id, name="Sede principal")
    session.add(location)
    await session.flush()
    room = Room(organization_id=organization_id, location_id=location.id, name="Sala 1")
    session.add(room)
    await session.flush()
    return room


def _appointment_payload(
    patient_id: str, practitioner_id: str, *, starts_at: datetime, room_id: str | None = None
) -> dict:
    payload = {
        "patient_id": patient_id,
        "practitioner_id": practitioner_id,
        "starts_at": starts_at.isoformat(),
        "ends_at": (starts_at + timedelta(minutes=30)).isoformat(),
    }
    if room_id is not None:
        payload["room_id"] = room_id
    return payload


async def test_booking_inside_availability_succeeds(client):
    ctx = await _setup(client)
    response = await client.post(
        "/api/v1/appointments",
        json=_appointment_payload(
            ctx["patient_id"], ctx["practitioner_id"], starts_at=_IN_WINDOW_START
        ),
        headers=ctx["headers"],
    )
    assert response.status_code == 201, response.text


async def test_booking_outside_availability_is_rejected(client):
    ctx = await _setup(client)
    # 03:00 UTC on the same Monday — outside the 09:00-17:00 rule.
    outside_start = datetime.combine(_NEXT_MONDAY, datetime.min.time(), tzinfo=UTC) + timedelta(
        hours=3
    )
    response = await client.post(
        "/api/v1/appointments",
        json=_appointment_payload(
            ctx["patient_id"], ctx["practitioner_id"], starts_at=outside_start
        ),
        headers=ctx["headers"],
    )
    assert response.status_code == 409, response.text


async def test_booking_with_a_patient_from_another_org_is_rejected(client):
    ctx = await _setup(client)
    other_org_patient_id = await _create_patient(client, (await _setup(client))["headers"])

    response = await client.post(
        "/api/v1/appointments",
        json=_appointment_payload(
            other_org_patient_id, ctx["practitioner_id"], starts_at=_IN_WINDOW_START
        ),
        headers=ctx["headers"],
    )
    assert response.status_code == 404, response.text


async def test_booking_with_a_practitioner_from_another_org_is_rejected(client):
    ctx = await _setup(client)
    other_ctx = await _setup(client)

    response = await client.post(
        "/api/v1/appointments",
        json=_appointment_payload(
            ctx["patient_id"], other_ctx["practitioner_id"], starts_at=_IN_WINDOW_START
        ),
        headers=ctx["headers"],
    )
    assert response.status_code == 404, response.text


async def test_booking_with_a_room_from_another_org_is_rejected(client):
    ctx = await _setup(client)
    other_ctx = await _setup(client)
    other_room = await _create_room(client.db_session, uuid.UUID(other_ctx["organization_id"]))

    response = await client.post(
        "/api/v1/appointments",
        json=_appointment_payload(
            ctx["patient_id"],
            ctx["practitioner_id"],
            starts_at=_IN_WINDOW_START,
            room_id=str(other_room.id),
        ),
        headers=ctx["headers"],
    )
    assert response.status_code == 404, response.text


async def test_double_booking_the_same_room_is_rejected(client):
    ctx = await _setup(client)
    room = await _create_room(client.db_session, uuid.UUID(ctx["organization_id"]))

    second_practitioner_id = await _create_practitioner(client, ctx["headers"])
    await _add_availability_rule(
        client, ctx["headers"], second_practitioner_id, _NEXT_MONDAY.weekday()
    )

    first = await client.post(
        "/api/v1/appointments",
        json=_appointment_payload(
            ctx["patient_id"],
            ctx["practitioner_id"],
            starts_at=_IN_WINDOW_START,
            room_id=str(room.id),
        ),
        headers=ctx["headers"],
    )
    assert first.status_code == 201, first.text

    # Same room, same time window, a *different* practitioner — the
    # practitioner-conflict check alone would let this through.
    second = await client.post(
        "/api/v1/appointments",
        json=_appointment_payload(
            ctx["patient_id"],
            second_practitioner_id,
            starts_at=_IN_WINDOW_START,
            room_id=str(room.id),
        ),
        headers=ctx["headers"],
    )
    assert second.status_code == 409, second.text


async def test_zero_duration_availability_query_is_rejected_not_hung(client):
    ctx = await _setup(client)
    response = await client.get(
        "/api/v1/appointments/availability",
        params={
            "practitioner_id": ctx["practitioner_id"],
            "date_from": _NEXT_MONDAY.isoformat(),
            "date_to": _NEXT_MONDAY.isoformat(),
            "duration_minutes": 0,
        },
        headers=ctx["headers"],
    )
    assert response.status_code == 422, response.text
