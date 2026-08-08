"""Cross-tenant isolation, role gating, and audit-trail coverage tests.

Companion to test_auth_flows.py — see that module's docstring for why these
run against a real database on one shared session-scoped loop with each
test's writes rolled back at teardown, rather than mocked repositories.

These specifically target the gaps found while scoping "audit coverage and
the server authorization review" (missing_features.md, "Authorization,
audit, and security"): clinical notes and treatment sessions/plans had no
organization-boundary check at all (any authenticated user from any org
could read or mutate another org's clinical records by UUID), and no
mutating endpoint recorded an audit event despite the audit model and
listing route already existing.
"""

import uuid
from itertools import pairwise

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
from medical_api.modules.audit.service import AuditService

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest_asyncio.fixture(loop_scope="session")
async def client():
    """Same external-transaction-plus-savepoint pattern as test_auth_flows.py's
    `client` fixture — see that module's docstring for the full rationale.
    The DB session is stashed on the client as `.db_session` so tests that
    need to inspect audit rows directly (hash-chain fields aren't exposed
    over the API by design) can query the same uncommitted transaction the
    app itself is writing to.
    """
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
            ac.db_session = session
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
        pytest.skip("no reachable database for authorization/audit integration tests")


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


async def _current_user(client, access_token: str) -> dict:
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200, response.text
    return response.json()


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


async def test_clinical_notes_are_org_scoped_and_role_gated(client):
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

    note = await client.post(
        "/api/v1/patients/clinical-notes",
        json={"patient_id": patient_a_id, "content": "Initial consult notes"},
        headers=practitioner_a_headers,
    )
    assert note.status_code == 201, note.text
    note_id = note.json()["id"]

    # Reception is barred from clinical content entirely, even for their own org.
    reception_read = await client.get(
        f"/api/v1/patients/{patient_a_id}/clinical-notes", headers=receptionist_a_headers
    )
    assert reception_read.status_code == 403

    # A practitioner in a different org is role-eligible but must see
    # nothing for another org's patient — org scoping, not just role
    # gating, has to hold.
    cross_org_read = await client.get(
        f"/api/v1/patients/{patient_a_id}/clinical-notes", headers=practitioner_b_headers
    )
    assert cross_org_read.status_code == 200
    assert cross_org_read.json() == []

    # Creating a note by supplying another org's patient_id must fail
    # rather than silently attaching cross-org data.
    cross_org_create = await client.post(
        "/api/v1/patients/clinical-notes",
        json={"patient_id": patient_a_id, "content": "Should not be allowed"},
        headers=practitioner_b_headers,
    )
    assert cross_org_create.status_code == 404

    # Finalizing another org's note by ID must 404, not silently succeed.
    cross_org_finalize = await client.post(
        f"/api/v1/patients/clinical-notes/{note_id}/finalize", headers=practitioner_b_headers
    )
    assert cross_org_finalize.status_code == 404

    own_org_finalize = await client.post(
        f"/api/v1/patients/clinical-notes/{note_id}/finalize", headers=practitioner_a_headers
    )
    assert own_org_finalize.status_code == 200
    assert own_org_finalize.json()["is_finalized"] is True


async def test_treatment_plans_and_sessions_are_org_scoped(client):
    org_a = await _register_org(client)
    admin_a_headers = {"Authorization": f"Bearer {org_a['access_token']}"}
    practitioner_a = await _invite_and_accept(client, admin_a_headers, "practitioner")
    practitioner_a_headers = {"Authorization": f"Bearer {practitioner_a['access_token']}"}

    org_b = await _register_org(client)
    admin_b_headers = {"Authorization": f"Bearer {org_b['access_token']}"}
    practitioner_b = await _invite_and_accept(client, admin_b_headers, "practitioner")
    practitioner_b_headers = {"Authorization": f"Bearer {practitioner_b['access_token']}"}

    patient_a_id = await _create_patient(client, practitioner_a_headers)

    definition = await client.post(
        "/api/v1/treatments/definitions",
        json={"name": "Standard cleaning", "default_session_count": 3},
        headers=admin_a_headers,
    )
    assert definition.status_code == 201, definition.text
    definition_id = definition.json()["id"]

    plan = await client.post(
        "/api/v1/treatments/plans",
        json={
            "patient_id": patient_a_id,
            "treatment_definition_id": definition_id,
            "planned_session_count": 3,
        },
        headers=practitioner_a_headers,
    )
    assert plan.status_code == 201, plan.text
    plan_id = plan.json()["id"]

    # Referencing org A's patient from org B must fail rather than create a
    # plan in org B that dangles a foreign patient_id.
    cross_org_plan = await client.post(
        "/api/v1/treatments/plans",
        json={
            "patient_id": patient_a_id,
            "treatment_definition_id": definition_id,
            "planned_session_count": 1,
        },
        headers=practitioner_b_headers,
    )
    assert cross_org_plan.status_code == 404

    # Listing another org's plan's sessions must 404, not return org A's
    # (possibly empty, but the point is the boundary) session list.
    cross_org_sessions = await client.get(
        f"/api/v1/treatments/plans/{plan_id}/sessions", headers=practitioner_b_headers
    )
    assert cross_org_sessions.status_code == 404

    own_org_sessions = await client.get(
        f"/api/v1/treatments/plans/{plan_id}/sessions", headers=practitioner_a_headers
    )
    assert own_org_sessions.status_code == 200
    assert own_org_sessions.json() == []


async def test_mutations_are_recorded_in_the_audit_trail(client):
    org = await _register_org(client)
    admin_headers = {"Authorization": f"Bearer {org['access_token']}"}

    patient_id = await _create_patient(client, admin_headers)

    audit_events = await client.get("/api/v1/audit", headers=admin_headers)
    assert audit_events.status_code == 200
    actions = [event["action"] for event in audit_events.json()]
    # register_organization itself is audited too, not just the later
    # patient creation.
    assert "patient.created" in actions
    assert "organization.registered" in actions

    patient_created_event = next(e for e in audit_events.json() if e["action"] == "patient.created")
    assert patient_created_event["resource_id"] == patient_id
    assert patient_created_event["actor_user_id"] is not None

    # A role with no audit access must not be able to read the trail at all.
    receptionist = await _invite_and_accept(client, admin_headers, "receptionist")
    receptionist_headers = {"Authorization": f"Bearer {receptionist['access_token']}"}
    forbidden = await client.get("/api/v1/audit", headers=receptionist_headers)
    assert forbidden.status_code == 403


async def test_audit_events_form_a_verifiable_hash_chain(client):
    org = await _register_org(client)
    organization_id = uuid.UUID(org["organization_id"])
    session = client.db_session
    service = AuditService(session)

    first = await service.record(
        organization_id=organization_id,
        actor_user_id=None,
        action="test.event_one",
        resource_type="test",
        resource_id="1",
    )
    second = await service.record(
        organization_id=organization_id,
        actor_user_id=None,
        action="test.event_two",
        resource_type="test",
        resource_id="2",
    )

    assert second.previous_hash == first.event_hash
    assert first.event_hash != second.event_hash

    stmt = (
        select(AuditEvent)
        .where(AuditEvent.organization_id == organization_id)
        .order_by(AuditEvent.sequence)
    )
    chain = list((await session.execute(stmt)).scalars().all())
    # register_organization's own audit event is first in the chain.
    assert chain[0].previous_hash is None
    for earlier, later in pairwise(chain):
        assert later.previous_hash == earlier.event_hash


async def test_role_updates_require_organization_admin_and_are_org_scoped(client):
    org = await _register_org(client)
    admin_headers = {"Authorization": f"Bearer {org['access_token']}"}
    medical_director = await _invite_and_accept(client, admin_headers, "medical_director")
    practitioner = await _invite_and_accept(client, admin_headers, "practitioner")
    practitioner_user = await _current_user(client, practitioner["access_token"])

    response = await client.patch(
        f"/api/v1/auth/users/{practitioner_user['id']}/roles",
        json={"roles": ["assistant"]},
        headers={"Authorization": f"Bearer {medical_director['access_token']}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"

    other_org = await _register_org(client)
    other_admin = await _current_user(client, other_org["access_token"])
    cross_org = await client.patch(
        f"/api/v1/auth/users/{other_admin['id']}/roles",
        json={"roles": ["assistant"]},
        headers=admin_headers,
    )
    assert cross_org.status_code == 404


async def test_last_organization_admin_cannot_be_demoted(client):
    org = await _register_org(client)
    admin_headers = {"Authorization": f"Bearer {org['access_token']}"}
    admin_user = await _current_user(client, org["access_token"])

    response = await client.patch(
        f"/api/v1/auth/users/{admin_user['id']}/roles",
        json={"roles": ["medical_director"]},
        headers=admin_headers,
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "The last organization administrator cannot be demoted. Assign another administrator first."
    )


async def test_role_update_replaces_roles_and_records_audit_metadata(client):
    org = await _register_org(client)
    organization_id = uuid.UUID(org["organization_id"])
    admin_headers = {"Authorization": f"Bearer {org['access_token']}"}
    admin_user = await _current_user(client, org["access_token"])
    practitioner = await _invite_and_accept(client, admin_headers, "practitioner")
    practitioner_user = await _current_user(client, practitioner["access_token"])

    response = await client.patch(
        f"/api/v1/auth/users/{practitioner_user['id']}/roles",
        json={"roles": ["assistant", "auditor"]},
        headers=admin_headers,
    )

    assert response.status_code == 200, response.text
    assert sorted(response.json()["roles"]) == ["assistant", "auditor"]

    stmt = select(AuditEvent).where(
        AuditEvent.organization_id == organization_id,
        AuditEvent.action == "user.role_updated",
        AuditEvent.resource_id == practitioner_user["id"],
    )
    event = (await client.db_session.execute(stmt)).scalar_one()
    assert event.actor_user_id == uuid.UUID(admin_user["id"])
    assert event.event_metadata == {
        "old_roles": ["practitioner"],
        "new_roles": ["assistant", "auditor"],
    }
