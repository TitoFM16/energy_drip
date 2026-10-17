"""The public MVP must create a real appointment and serialize competing bookings."""

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from medical_api.core.config import get_settings
from medical_api.core.database import async_session_factory, engine, get_db
from medical_api.core.exceptions import ConflictError, NotFoundError
from medical_api.main import app
from medical_api.modules.booking.schemas import PublicAppointmentCreate
from medical_api.modules.booking.service import book_public_appointment
from medical_api.modules.identity.models import User
from medical_api.modules.organizations.models import Organization
from medical_api.modules.patients.models import Patient
from medical_api.modules.scheduling.models import Appointment, AvailabilityRule, Practitioner
from medical_api.modules.treatments.models import TreatmentDefinition
from medical_api.modules.treatments.repository import TreatmentDefinitionRepository

pytestmark = pytest.mark.asyncio(loop_scope="session")
DAY = datetime.now(UTC).date() + timedelta(days=7)
START = datetime.combine(DAY, datetime.min.time(), tzinfo=ZoneInfo("America/Bogota")) + timedelta(
    hours=9
)


@pytest_asyncio.fixture(loop_scope="session")
async def client():
    connection = await engine.connect()
    transaction = await connection.begin()
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
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            client.db_session = session
            yield client
    finally:
        del app.dependency_overrides[get_db]
        await session.close()
        await transaction.rollback()
        await connection.close()


async def setup_clinic(client, monkeypatch):
    response = await client.post(
        "/api/v1/auth/register-organization",
        json={
            "organization_name": "MVP clinic",
            "admin_email": f"{uuid.uuid4()}@example.com",
            "admin_password": "secure-test-password",
            "admin_full_name": "Owner",
        },
    )
    assert response.status_code == 201, response.text
    org = response.json()
    monkeypatch.setattr(get_settings(), "public_organization_id", uuid.UUID(org["organization_id"]))
    headers = {"Authorization": f"Bearer {org['access_token']}"}
    worker = await client.post(
        "/api/v1/practitioners",
        headers=headers,
        json={"full_name": "Nurse Ana", "specialty": "Enfermería"},
    )
    assert worker.status_code == 201, worker.text
    worker = worker.json()
    service = await client.post(
        "/api/v1/treatments/definitions",
        headers=headers,
        json={
            "name": "Consulta",
            "description": "Consulta profesional",
            "price": "85000.00",
            "currency": "COP",
            "duration_minutes": 30,
            "image_url": "https://example.com/consultation.jpg",
        },
    )
    assert service.status_code == 201, service.text
    service = service.json()
    rule = await client.post(
        "/api/v1/appointments/availability-rules",
        headers=headers,
        json={
            "practitioner_id": worker["id"],
            "weekday": DAY.weekday(),
            "start_time": "09:00",
            "end_time": "12:00",
        },
    )
    assert rule.status_code == 201, rule.text
    return headers, worker, service


def payload(worker, service, start=START):
    return {
        "practitioner_id": worker["id"],
        "treatment_definition_id": service["id"],
        "starts_at": start.isoformat(),
        "first_name": "Elena",
        "last_name": "García",
        "phone_number": "+573001112233",
    }


async def test_public_catalogue_booking_admin_management_and_cancellation(client, monkeypatch):
    headers, worker, service = await setup_clinic(client, monkeypatch)
    catalogue = (await client.get("/api/v1/public/treatments")).json()
    assert catalogue[0]["price"] == "85000.00"
    assert catalogue[0]["duration_minutes"] == 30
    workers = (await client.get("/api/v1/public/practitioners")).json()
    assert workers == [{"id": worker["id"], "full_name": "Nurse Ana", "specialty": "Enfermería"}]
    slots_url = (
        f"/api/v1/public/availability?practitioner_id={worker['id']}"
        f"&treatment_definition_id={service['id']}&date_from={DAY}&date_to={DAY}"
    )
    slots = (await client.get(slots_url)).json()
    assert len(slots) == 6
    assert datetime.fromisoformat(slots[0]["starts_at"]) == START
    assert datetime.fromisoformat(slots[0]["starts_at"]).utcoffset() == timedelta(hours=-5)
    booking = await client.post("/api/v1/public/appointments", json=payload(worker, service))
    assert booking.status_code == 201, booking.text
    assert booking.json()["status"] == "confirmed"
    assert booking.json()["practitioner_name"] == "Nurse Ana"
    assert len((await client.get(slots_url)).json()) == 5
    duplicate = await client.post("/api/v1/public/appointments", json=payload(worker, service))
    assert duplicate.status_code == 409, duplicate.text
    appointments = await client.get(
        "/api/v1/appointments",
        headers=headers,
        params={"start": START.isoformat(), "end": (START + timedelta(days=1)).isoformat()},
    )
    item = appointments.json()[0]
    assert item["patient_name"] == "Elena García"
    assert item["patient_phone"] == "+573001112233"
    assert item["treatment_name"] == "Consulta"
    assert item["treatment_definition_id"] == service["id"]
    # Changing the advertised duration does not change an already booked duration.
    await client.patch(
        f"/api/v1/treatments/definitions/{service['id']}",
        headers=headers,
        json={"duration_minutes": 60},
    )
    moved = await client.patch(
        f"/api/v1/appointments/{item['id']}/reschedule",
        headers=headers,
        json={
            "starts_at": (START + timedelta(hours=1)).isoformat(),
            "ends_at": (START + timedelta(minutes=90)).isoformat(),
        },
    )
    assert moved.status_code == 200, moved.text
    cancelled = await client.post(
        f"/api/v1/appointments/{item['id']}/status", headers=headers, json={"status": "cancelled"}
    )
    assert cancelled.status_code == 200, cancelled.text
    restore = await client.post(
        f"/api/v1/appointments/{item['id']}/status", headers=headers, json={"status": "confirmed"}
    )
    assert restore.status_code == 409


async def test_public_booking_rejects_invalid_slots_inactive_and_foreign_resources(
    client, monkeypatch
):
    headers, worker, service = await setup_clinic(client, monkeypatch)
    for start in [
        START + timedelta(minutes=5),
        START - timedelta(hours=1),
        START - timedelta(days=14),
    ]:
        response = await client.post(
            "/api/v1/public/appointments", json=payload(worker, service, start)
        )
        assert response.status_code == 409, response.text
    for field in ["practitioner_id", "treatment_definition_id"]:
        data = payload(worker, service)
        data[field] = str(uuid.uuid4())
        response = await client.post("/api/v1/public/appointments", json=data)
        assert response.status_code == 404, response.text
    data = payload(worker, service)
    data["website"] = "spam"
    assert (await client.post("/api/v1/public/appointments", json=data)).status_code == 409
    await client.patch(
        f"/api/v1/practitioners/{worker['id']}", headers=headers, json={"is_active": False}
    )
    assert (await client.get("/api/v1/public/practitioners")).json() == []
    staff_slots = await client.get(
        "/api/v1/appointments/availability",
        headers=headers,
        params={
            "practitioner_id": worker["id"],
            "date_from": DAY.isoformat(),
            "date_to": DAY.isoformat(),
            "duration_minutes": 30,
        },
    )
    assert staff_slots.status_code == 200
    assert staff_slots.json() == []
    missing_worker_slots = await client.get(
        "/api/v1/appointments/availability",
        headers=headers,
        params={
            "practitioner_id": str(uuid.uuid4()),
            "date_from": DAY.isoformat(),
            "date_to": DAY.isoformat(),
        },
    )
    assert missing_worker_slots.status_code == 404
    assert (
        await client.post("/api/v1/public/appointments", json=payload(worker, service))
    ).status_code == 404
    await client.patch(
        f"/api/v1/treatments/definitions/{service['id']}",
        headers=headers,
        json={"is_active": False},
    )
    assert (await client.get("/api/v1/public/treatments")).json() == []


async def test_validation_and_staff_only_mutations(client, monkeypatch):
    headers, worker, service = await setup_clinic(client, monkeypatch)
    for patch in [
        {"price": "-1"},
        {"duration_minutes": 0},
        {"name": " "},
        {"image_url": "javascript:alert(1)"},
        {"price": None},
    ]:
        response = await client.patch(
            f"/api/v1/treatments/definitions/{service['id']}", headers=headers, json=patch
        )
        assert response.status_code == 422, response.text
    foreign_rule = await client.post(
        "/api/v1/appointments/availability-rules",
        headers=headers,
        json={
            "practitioner_id": str(uuid.uuid4()),
            "weekday": 0,
            "start_time": "09:00",
            "end_time": "10:00",
        },
    )
    assert foreign_rule.status_code == 404
    assert (
        await client.post("/api/v1/treatments/definitions", json={"name": "No authorization"})
    ).status_code == 401
    naive = payload(worker, service)
    naive["starts_at"] = "2030-01-01T09:00:00"
    assert (await client.post("/api/v1/public/appointments", json=naive)).status_code == 422


async def test_public_clinic_resolution_fails_closed(client, monkeypatch):
    await setup_clinic(client, monkeypatch)
    client.db_session.add(Organization(name="Another clinic"))
    await client.db_session.commit()
    monkeypatch.setattr(get_settings(), "public_organization_id", None)
    assert (await client.get("/api/v1/public/treatments")).json() == []
    assert (await client.get("/api/v1/public/practitioners")).json() == []


@pytest_asyncio.fixture(loop_scope="session")
async def committed_clinic():
    # A real committed fixture and two independent DB connections, not an AsyncMock.
    async with async_session_factory() as session:
        org = Organization(name="Concurrent booking test")
        session.add(org)
        await session.flush()
        user = User(
            organization_id=org.id,
            full_name="Nurse",
            email=f"{uuid.uuid4()}@example.com",
            hashed_password="disabled",
            is_active=False,
        )
        service = TreatmentDefinition(organization_id=org.id, name="Consulta", duration_minutes=30)
        session.add_all([user, service])
        await session.flush()
        worker = Practitioner(organization_id=org.id, user_id=user.id)
        session.add(worker)
        await session.flush()
        session.add(
            AvailabilityRule(
                organization_id=org.id,
                practitioner_id=worker.id,
                weekday=DAY.weekday(),
                start_time=START.time(),
                end_time=(START + timedelta(hours=1)).time(),
            )
        )
        await session.commit()
        org_id, worker_id, service_id = org.id, worker.id, service.id
    try:
        yield org_id, worker_id, service_id
    finally:
        async with async_session_factory() as session:
            for model in [
                Appointment,
                AvailabilityRule,
                Patient,
                Practitioner,
                TreatmentDefinition,
                User,
            ]:
                await session.execute(delete(model).where(model.organization_id == org_id))
            await session.execute(delete(Organization).where(Organization.id == org_id))
            await session.commit()


async def test_two_concurrent_transactions_cannot_book_same_worker_slot(committed_clinic):
    org_id, worker_id, service_id = committed_clinic
    ready = asyncio.Event()

    async def book():
        async with async_session_factory() as session:
            await ready.wait()
            try:
                result = await book_public_appointment(
                    session,
                    org_id,
                    PublicAppointmentCreate(
                        practitioner_id=worker_id,
                        treatment_definition_id=service_id,
                        starts_at=START,
                        first_name="Elena",
                        last_name="García",
                        phone_number="3001112233",
                    ),
                )
                await session.commit()
                return result
            except ConflictError:
                await session.rollback()
                return None

    tasks = [asyncio.create_task(book()) for _ in range(2)]
    ready.set()
    results = await asyncio.wait_for(asyncio.gather(*tasks), timeout=10)
    assert sum(result is not None for result in results) == 1
    async with async_session_factory() as session:
        assert (
            await session.scalar(
                select(func.count())
                .select_from(Appointment)
                .where(Appointment.organization_id == org_id)
            )
            == 1
        )
        assert (
            await session.scalar(
                select(func.count()).select_from(Patient).where(Patient.organization_id == org_id)
            )
            == 1
        )


async def test_booking_refreshes_service_deactivated_in_another_transaction(committed_clinic):
    org_id, worker_id, service_id = committed_clinic
    async with async_session_factory() as stale_session:
        cached = await TreatmentDefinitionRepository(stale_session).get(org_id, service_id)
        assert cached.is_active
        async with async_session_factory() as edit_session:
            service = await TreatmentDefinitionRepository(edit_session).get(
                org_id, service_id, for_update=True
            )
            service.is_active = False
            await edit_session.commit()
        # The same ORM identity is still cached as active until the locked refresh.
        assert cached.is_active
        with pytest.raises(NotFoundError):
            await book_public_appointment(
                stale_session,
                org_id,
                PublicAppointmentCreate(
                    practitioner_id=worker_id,
                    treatment_definition_id=service_id,
                    starts_at=START,
                    first_name="Elena",
                    last_name="García",
                    phone_number="3001112233",
                ),
            )
        assert cached.is_active is False
        await stale_session.rollback()
    async with async_session_factory() as session:
        count = await session.scalar(
            select(func.count())
            .select_from(Appointment)
            .where(Appointment.organization_id == org_id)
        )
        assert count == 0
