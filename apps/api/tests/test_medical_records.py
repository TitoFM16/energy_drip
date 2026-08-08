"""Coverage for the medical-history/allergies/conditions/medications APIs
added to close the "Complete medical-record API" gap in
missing_features.md. Same real-database-plus-savepoint pattern as
test_authorization_and_audit.py — see that module's docstring, and
test_auth_flows.py's `client` fixture, for the full rationale.

None of these four models carry their own organization_id (same shape of
gap fixed for ClinicalNote and TreatmentSession — see
test_authorization_and_audit.py), so org-scoping and role-gating are
exercised here the same way: cross-org reads must come back empty,
cross-org mutations by patient_id or by-ID must 404 rather than silently
succeed, and reception must be barred from clinical content entirely.
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
        pytest.skip("no reachable database for medical-record integration tests")


async def _register_org(client) -> dict:
    response = await client.post(
        "/api/v1/auth/register-organization",
        json={
            "organization_name": f"Test Clinic {uuid.uuid4()}",
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
        "/api/v1/auth/invites",
        json={"email": email, "role": role},
        headers=admin_headers,
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
        json={
            "first_name": "Jane",
            "last_name": "Doe",
            "document_id": f"doc-{uuid.uuid4()}",
            "phone_number": "+573001112233",
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def _two_orgs_with_a_patient(client) -> dict:
    org_a = await _register_org(client)
    admin_a_headers = {"Authorization": f"Bearer {org_a['access_token']}"}
    practitioner_a = await _invite_and_accept(client, admin_a_headers, "practitioner")
    practitioner_a_headers = {"Authorization": f"Bearer {practitioner_a['access_token']}"}
    receptionist_a = await _invite_and_accept(client, admin_a_headers, "receptionist")
    receptionist_a_headers = {"Authorization": f"Bearer {receptionist_a['access_token']}"}

    org_b = await _register_org(client)
    admin_b_headers = {"Authorization": f"Bearer {org_b['access_token']}"}
    practitioner_b = await _invite_and_accept(client, admin_b_headers, "practitioner")
    practitioner_b_headers = {"Authorization": f"Bearer {practitioner_b['access_token']}"}

    patient_a_id = await _create_patient(client, practitioner_a_headers)

    return {
        "admin_a_headers": admin_a_headers,
        "practitioner_a_headers": practitioner_a_headers,
        "receptionist_a_headers": receptionist_a_headers,
        "practitioner_b_headers": practitioner_b_headers,
        "patient_a_id": patient_a_id,
    }


@pytest.mark.parametrize(
    ("resource", "list_path", "create_path", "create_body"),
    [
        (
            "allergies",
            "allergies",
            "/api/v1/patients/allergies",
            lambda patient_id: {"patient_id": patient_id, "substance": "Penicillin"},
        ),
        (
            "conditions",
            "conditions",
            "/api/v1/patients/conditions",
            lambda patient_id: {"patient_id": patient_id, "name": "Hypertension"},
        ),
        (
            "medications",
            "medications",
            "/api/v1/patients/medications",
            lambda patient_id: {"patient_id": patient_id, "name": "Losartan"},
        ),
    ],
)
async def test_resource_is_org_scoped_and_role_gated(
    client, resource, list_path, create_path, create_body
):
    ctx = await _two_orgs_with_a_patient(client)
    patient_a_id = ctx["patient_a_id"]

    created = await client.post(
        create_path,
        json=create_body(patient_a_id),
        headers=ctx["practitioner_a_headers"],
    )
    assert created.status_code == 201, created.text

    # Reception is barred from clinical content entirely, even for their
    # own org's patient.
    reception_read = await client.get(
        f"/api/v1/patients/{patient_a_id}/{list_path}", headers=ctx["receptionist_a_headers"]
    )
    assert reception_read.status_code == 403

    # A practitioner in a different org is role-eligible but must see
    # nothing for another org's patient.
    cross_org_read = await client.get(
        f"/api/v1/patients/{patient_a_id}/{list_path}", headers=ctx["practitioner_b_headers"]
    )
    assert cross_org_read.status_code == 200
    assert cross_org_read.json() == []

    # Creating an entry by supplying another org's patient_id must fail
    # rather than silently attaching cross-org data.
    cross_org_create = await client.post(
        create_path,
        json=create_body(patient_a_id),
        headers=ctx["practitioner_b_headers"],
    )
    assert cross_org_create.status_code == 404

    own_org_read = await client.get(
        f"/api/v1/patients/{patient_a_id}/{list_path}", headers=ctx["practitioner_a_headers"]
    )
    assert own_org_read.status_code == 200
    assert len(own_org_read.json()) == 1


async def test_allergy_update_and_deactivate(client):
    ctx = await _two_orgs_with_a_patient(client)
    patient_a_id = ctx["patient_a_id"]

    created = await client.post(
        "/api/v1/patients/allergies",
        json={"patient_id": patient_a_id, "substance": "Latex", "severity": "mild"},
        headers=ctx["practitioner_a_headers"],
    )
    assert created.status_code == 201, created.text
    allergy_id = created.json()["id"]

    # Cross-org update by ID must 404, not silently mutate another org's row.
    cross_org_update = await client.patch(
        f"/api/v1/patients/allergies/{allergy_id}",
        json={"severity": "severe"},
        headers=ctx["practitioner_b_headers"],
    )
    assert cross_org_update.status_code == 404

    updated = await client.patch(
        f"/api/v1/patients/allergies/{allergy_id}",
        json={"severity": "severe"},
        headers=ctx["practitioner_a_headers"],
    )
    assert updated.status_code == 200
    assert updated.json()["severity"] == "severe"

    deactivated = await client.patch(
        f"/api/v1/patients/allergies/{allergy_id}",
        json={"is_active": False},
        headers=ctx["practitioner_a_headers"],
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False
    # Substance/severity from the earlier update must not have been reset —
    # exclude_unset means a deactivate-only PATCH shouldn't touch other fields.
    assert deactivated.json()["severity"] == "severe"


async def test_medication_is_current_toggle(client):
    ctx = await _two_orgs_with_a_patient(client)
    patient_a_id = ctx["patient_a_id"]

    created = await client.post(
        "/api/v1/patients/medications",
        json={"patient_id": patient_a_id, "name": "Ibuprofen", "dosage": "400mg"},
        headers=ctx["practitioner_a_headers"],
    )
    assert created.status_code == 201, created.text
    assert created.json()["is_current"] is True

    stopped = await client.patch(
        f"/api/v1/patients/medications/{created.json()['id']}",
        json={"is_current": False},
        headers=ctx["practitioner_a_headers"],
    )
    assert stopped.status_code == 200
    assert stopped.json()["is_current"] is False


async def test_medical_history_finalize_is_one_way_and_org_scoped(client):
    ctx = await _two_orgs_with_a_patient(client)
    patient_a_id = ctx["patient_a_id"]

    entry = await client.post(
        "/api/v1/patients/medical-history",
        json={"patient_id": patient_a_id, "summary": "No known chronic conditions."},
        headers=ctx["practitioner_a_headers"],
    )
    assert entry.status_code == 201, entry.text
    entry_id = entry.json()["id"]
    assert entry.json()["is_finalized"] is False

    cross_org_finalize = await client.post(
        f"/api/v1/patients/medical-history/{entry_id}/finalize",
        headers=ctx["practitioner_b_headers"],
    )
    assert cross_org_finalize.status_code == 404

    finalized = await client.post(
        f"/api/v1/patients/medical-history/{entry_id}/finalize",
        headers=ctx["practitioner_a_headers"],
    )
    assert finalized.status_code == 200
    assert finalized.json()["is_finalized"] is True
    assert finalized.json()["finalized_at"] is not None

    # Finalizing twice must be rejected, not silently re-finalize.
    already_finalized = await client.post(
        f"/api/v1/patients/medical-history/{entry_id}/finalize",
        headers=ctx["practitioner_a_headers"],
    )
    assert already_finalized.status_code == 409


async def test_medical_history_amendment_flow(client):
    ctx = await _two_orgs_with_a_patient(client)
    patient_a_id = ctx["patient_a_id"]

    original = await client.post(
        "/api/v1/patients/medical-history",
        json={"patient_id": patient_a_id, "summary": "Allergic to none."},
        headers=ctx["practitioner_a_headers"],
    )
    assert original.status_code == 201, original.text
    original_id = original.json()["id"]
    await client.post(
        f"/api/v1/patients/medical-history/{original_id}/finalize",
        headers=ctx["practitioner_a_headers"],
    )

    # Correcting a finalized entry never edits it in place — a new entry is
    # created referencing the one it amends.
    correction = await client.post(
        "/api/v1/patients/medical-history",
        json={
            "patient_id": patient_a_id,
            "summary": "Correction: allergic to penicillin.",
            "amends_entry_id": original_id,
        },
        headers=ctx["practitioner_a_headers"],
    )
    assert correction.status_code == 201, correction.text
    assert correction.json()["amends_entry_id"] == original_id

    history = await client.get(
        f"/api/v1/patients/{patient_a_id}/medical-history",
        headers=ctx["practitioner_a_headers"],
    )
    assert history.status_code == 200
    assert len(history.json()) == 2
    original_entry = next(e for e in history.json() if e["id"] == original_id)
    assert original_entry["summary"] == "Allergic to none."
    assert original_entry["is_finalized"] is True

    # amends_entry_id referencing an entry belonging to a different patient
    # must be rejected as not found, rather than linking across patients.
    other_patient_id = await _create_patient(client, ctx["practitioner_a_headers"])
    cross_patient_amend = await client.post(
        "/api/v1/patients/medical-history",
        json={
            "patient_id": other_patient_id,
            "summary": "Should be rejected",
            "amends_entry_id": original_id,
        },
        headers=ctx["practitioner_a_headers"],
    )
    assert cross_patient_amend.status_code == 404


async def test_medical_record_mutations_are_audited(client):
    ctx = await _two_orgs_with_a_patient(client)
    patient_a_id = ctx["patient_a_id"]

    allergy = await client.post(
        "/api/v1/patients/allergies",
        json={"patient_id": patient_a_id, "substance": "Pollen"},
        headers=ctx["practitioner_a_headers"],
    )
    assert allergy.status_code == 201, allergy.text

    audit_events = await client.get("/api/v1/audit", headers=ctx["admin_a_headers"])
    assert audit_events.status_code == 200
    events = audit_events.json()
    allergy_event = next(e for e in events if e["action"] == "allergy.created")
    assert allergy_event["resource_id"] == allergy.json()["id"]
    assert allergy_event["actor_user_id"] is not None
