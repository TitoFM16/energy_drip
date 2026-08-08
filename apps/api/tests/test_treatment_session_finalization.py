"""Real-PostgreSQL coverage for treatment-session finalization.

The fixture mirrors test_medical_records.py: application requests and direct
audit inspection share one external transaction so no authorization,
organization-scoping, or persistence behavior is mocked.
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
from medical_api.modules.audit.models import AuditEvent

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest_asyncio.fixture(loop_scope="session")
async def client():
    connection = await engine.connect()
    outer_transaction = await connection.begin()
    session = AsyncSession(
        bind=connection,
        join_transaction_mode="create_savepoint",
        expire_on_commit=False,
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
        pytest.skip("no reachable database for treatment-session integration tests")


async def _register_org(client: AsyncClient) -> dict:
    response = await client.post(
        "/api/v1/auth/register-organization",
        json={
            "organization_name": f"Treatment Clinic {uuid.uuid4()}",
            "admin_email": f"admin-{uuid.uuid4()}@example.com",
            "admin_password": "supersecret123",
            "admin_full_name": "Treatment Admin",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _invite_and_accept(client: AsyncClient, admin_headers: dict[str, str], role: str) -> dict:
    invite = await client.post(
        "/api/v1/auth/invites",
        json={"email": f"{role}-{uuid.uuid4()}@example.com", "role": role},
        headers=admin_headers,
    )
    assert invite.status_code == 201, invite.text
    accepted = await client.post(
        f"/api/v1/auth/invites/{invite.json()['token']}/accept",
        json={"full_name": role.title(), "password": "somesecretpw123"},
    )
    assert accepted.status_code == 201, accepted.text
    return accepted.json()


async def _create_session(client: AsyncClient) -> dict:
    org = await _register_org(client)
    admin_headers = {"Authorization": f"Bearer {org['access_token']}"}
    practitioner = await _invite_and_accept(client, admin_headers, "practitioner")
    practitioner_headers = {"Authorization": f"Bearer {practitioner['access_token']}"}
    practitioner_user = await client.get("/api/v1/auth/me", headers=practitioner_headers)
    assert practitioner_user.status_code == 200, practitioner_user.text

    patient = await client.post(
        "/api/v1/patients",
        json={"first_name": "Lucía", "last_name": "Sesión"},
        headers=admin_headers,
    )
    assert patient.status_code == 201, patient.text

    definition = await client.post(
        "/api/v1/treatments/definitions",
        json={"name": "Terapia intravenosa", "default_session_count": 1},
        headers=admin_headers,
    )
    assert definition.status_code == 201, definition.text

    plan = await client.post(
        "/api/v1/treatments/plans",
        json={
            "patient_id": patient.json()["id"],
            "treatment_definition_id": definition.json()["id"],
            "planned_session_count": 1,
        },
        headers=practitioner_headers,
    )
    assert plan.status_code == 201, plan.text

    treatment_session = await client.post(
        "/api/v1/treatments/sessions",
        json={
            "treatment_plan_id": plan.json()["id"],
            "practitioner_id": practitioner_user.json()["id"],
            "session_number": 1,
            "clinical_evolution": "Buena tolerancia, sin reacciones adversas.",
        },
        headers=practitioner_headers,
    )
    assert treatment_session.status_code == 201, treatment_session.text
    return {
        "admin_headers": admin_headers,
        "practitioner_headers": practitioner_headers,
        "plan_id": plan.json()["id"],
        "session": treatment_session.json(),
    }


async def test_finalize_session_is_role_gated_and_org_scoped(client: AsyncClient):
    context = await _create_session(client)
    session_id = context["session"]["id"]

    receptionist = await _invite_and_accept(client, context["admin_headers"], "receptionist")
    receptionist_headers = {"Authorization": f"Bearer {receptionist['access_token']}"}
    forbidden = await client.post(
        f"/api/v1/treatments/sessions/{session_id}/finalize",
        headers=receptionist_headers,
    )
    assert forbidden.status_code == 403

    other_org = await _register_org(client)
    other_admin_headers = {"Authorization": f"Bearer {other_org['access_token']}"}
    other_practitioner = await _invite_and_accept(client, other_admin_headers, "practitioner")
    cross_org = await client.post(
        f"/api/v1/treatments/sessions/{session_id}/finalize",
        headers={"Authorization": f"Bearer {other_practitioner['access_token']}"},
    )
    assert cross_org.status_code == 404


async def test_finalize_session_is_one_way_and_audited(client: AsyncClient):
    context = await _create_session(client)
    session_id = context["session"]["id"]
    assert context["session"]["is_finalized"] is False
    assert context["session"]["finalized_at"] is None

    finalized = await client.post(
        f"/api/v1/treatments/sessions/{session_id}/finalize",
        headers=context["practitioner_headers"],
    )
    assert finalized.status_code == 200, finalized.text
    finalized_body = finalized.json()
    assert finalized_body["is_finalized"] is True
    assert finalized_body["finalized_at"] is not None
    assert finalized_body["clinical_evolution"] == context["session"]["clinical_evolution"]

    already_finalized = await client.post(
        f"/api/v1/treatments/sessions/{session_id}/finalize",
        headers=context["practitioner_headers"],
    )
    assert already_finalized.status_code == 409

    sessions = await client.get(
        f"/api/v1/treatments/plans/{context['plan_id']}/sessions",
        headers=context["practitioner_headers"],
    )
    assert sessions.status_code == 200, sessions.text
    persisted = sessions.json()[0]
    assert persisted["is_finalized"] is True
    assert persisted["finalized_at"] == finalized_body["finalized_at"]
    assert persisted["clinical_evolution"] == context["session"]["clinical_evolution"]

    audit_event = (
        await client.db_session.execute(
            select(AuditEvent).where(
                AuditEvent.action == "treatment_session.finalized",
                AuditEvent.resource_id == session_id,
            )
        )
    ).scalar_one()
    assert audit_event.actor_user_id is not None
    assert audit_event.resource_type == "treatment_session"
    assert audit_event.event_metadata == {"treatment_plan_id": context["plan_id"]}
