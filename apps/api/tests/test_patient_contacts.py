"""Coverage for "Contact details and emergency contacts" under "Patient
management" in missing_features.md: `PatientContact` and `EmergencyContact`
existed only as bare database models with no API or UI. Same
real-database-plus-savepoint pattern as test_medical_records.py — see that
module's docstring for the full rationale. Unlike allergies/conditions/
medications (clinical data, gated to practitioner/medical_director), these
are demographic/administrative fields — gated the same way as Patient
create/update itself (receptionist and up).
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
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        del app.dependency_overrides[get_db]
        await session.close()
        await outer_transaction.rollback()
        await connection.close()


async def _db_reachable() -> bool:
    probe_engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
    try:
        async with probe_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
    finally:
        await probe_engine.dispose()


@pytest.fixture(autouse=True, scope="session")
async def _skip_without_db():
    if not await _db_reachable():
        pytest.skip("no reachable database for patient-contacts tests")


async def _register_org(client) -> dict:
    response = await client.post(
        "/api/v1/auth/register-organization",
        json={
            "organization_name": f"Contacts Clinic {uuid.uuid4()}",
            "admin_email": f"admin-{uuid.uuid4()}@example.com",
            "admin_password": "supersecret123",
            "admin_full_name": "Admin Person",
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


async def _create_patient(client, headers: dict) -> str:
    response = await client.post(
        "/api/v1/patients",
        json={"first_name": "Jane", "last_name": "Doe", "phone_number": "+573001112233"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def _setup(client) -> dict:
    org = await _register_org(client)
    admin_headers = {"Authorization": f"Bearer {org['access_token']}"}
    auditor = await _invite_and_accept(client, admin_headers, "auditor")
    auditor_headers = {"Authorization": f"Bearer {auditor['access_token']}"}
    patient_id = await _create_patient(client, admin_headers)
    return {
        "organization_id": org["organization_id"],
        "admin_headers": admin_headers,
        "auditor_headers": auditor_headers,
        "patient_id": patient_id,
    }


@pytest.mark.parametrize(
    ("resource", "list_path", "create_path", "create_body"),
    [
        (
            "contacts",
            "contacts",
            "/api/v1/patients/contacts",
            lambda patient_id: {
                "patient_id": patient_id,
                "label": "Trabajo",
                "phone_number": "+573001112233",
            },
        ),
        (
            "emergency-contacts",
            "emergency-contacts",
            "/api/v1/patients/emergency-contacts",
            lambda patient_id: {
                "patient_id": patient_id,
                "full_name": "Maria Doe",
                "relationship": "Madre",
                "phone_number": "+573009998877",
            },
        ),
    ],
)
async def test_contact_is_org_scoped_and_role_gated(
    client, resource, list_path, create_path, create_body
):
    ctx = await _setup(client)
    other_org = await _register_org(client)
    other_headers = {"Authorization": f"Bearer {other_org['access_token']}"}

    forbidden = await client.post(
        create_path, json=create_body(ctx["patient_id"]), headers=ctx["auditor_headers"]
    )
    assert forbidden.status_code == 403

    created = await client.post(
        create_path, json=create_body(ctx["patient_id"]), headers=ctx["admin_headers"]
    )
    assert created.status_code == 201, created.text
    contact_id = created.json()["id"]

    cross_org_create = await client.post(
        create_path, json=create_body(ctx["patient_id"]), headers=other_headers
    )
    assert cross_org_create.status_code == 404

    own_org_list = await client.get(
        f"/api/v1/patients/{ctx['patient_id']}/{list_path}", headers=ctx["admin_headers"]
    )
    assert own_org_list.status_code == 200
    assert len(own_org_list.json()) == 1

    cross_org_update = await client.patch(
        f"{create_path}/{contact_id}", json={}, headers=other_headers
    )
    assert cross_org_update.status_code == 404

    cross_org_delete = await client.delete(f"{create_path}/{contact_id}", headers=other_headers)
    assert cross_org_delete.status_code == 404


async def test_patient_contact_update_and_delete(client):
    ctx = await _setup(client)
    created = await client.post(
        "/api/v1/patients/contacts",
        json={"patient_id": ctx["patient_id"], "label": "Trabajo", "phone_number": "+573001112233"},
        headers=ctx["admin_headers"],
    )
    assert created.status_code == 201, created.text
    contact_id = created.json()["id"]

    updated = await client.patch(
        f"/api/v1/patients/contacts/{contact_id}",
        json={"label": "Casa"},
        headers=ctx["admin_headers"],
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["label"] == "Casa"
    assert updated.json()["phone_number"] == "+573001112233"

    deleted = await client.delete(
        f"/api/v1/patients/contacts/{contact_id}", headers=ctx["admin_headers"]
    )
    assert deleted.status_code == 204

    listing = await client.get(
        f"/api/v1/patients/{ctx['patient_id']}/contacts", headers=ctx["admin_headers"]
    )
    assert listing.json() == []


async def test_emergency_contact_update_and_delete(client):
    ctx = await _setup(client)
    created = await client.post(
        "/api/v1/patients/emergency-contacts",
        json={
            "patient_id": ctx["patient_id"],
            "full_name": "Maria Doe",
            "relationship": "Madre",
            "phone_number": "+573009998877",
        },
        headers=ctx["admin_headers"],
    )
    assert created.status_code == 201, created.text
    contact_id = created.json()["id"]

    updated = await client.patch(
        f"/api/v1/patients/emergency-contacts/{contact_id}",
        json={"relationship": "Tia"},
        headers=ctx["admin_headers"],
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["relationship"] == "Tia"
    assert updated.json()["full_name"] == "Maria Doe"

    deleted = await client.delete(
        f"/api/v1/patients/emergency-contacts/{contact_id}", headers=ctx["admin_headers"]
    )
    assert deleted.status_code == 204

    listing = await client.get(
        f"/api/v1/patients/{ctx['patient_id']}/emergency-contacts", headers=ctx["admin_headers"]
    )
    assert listing.json() == []


async def test_contact_mutations_are_audited(client):
    ctx = await _setup(client)
    created = await client.post(
        "/api/v1/patients/contacts",
        json={"patient_id": ctx["patient_id"], "label": "Trabajo"},
        headers=ctx["admin_headers"],
    )
    assert created.status_code == 201, created.text
    contact_id = created.json()["id"]

    await client.delete(f"/api/v1/patients/contacts/{contact_id}", headers=ctx["admin_headers"])

    audit_events = await client.get("/api/v1/audit", headers=ctx["admin_headers"])
    assert audit_events.status_code == 200
    actions = {e["action"] for e in audit_events.json()}
    assert "patient_contact.created" in actions
    assert "patient_contact.deleted" in actions


async def test_document_id_and_date_of_birth_are_editable(client):
    ctx = await _setup(client)
    updated = await client.patch(
        f"/api/v1/patients/{ctx['patient_id']}",
        json={"document_id": "CC123456789", "date_of_birth": "1990-05-15"},
        headers=ctx["admin_headers"],
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["document_id"] == "CC123456789"
    assert updated.json()["date_of_birth"] == "1990-05-15"
