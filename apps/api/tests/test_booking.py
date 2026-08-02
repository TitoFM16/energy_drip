"""Public booking-request flow: honeypot filtering, cross-org validation,
staff-side visibility/role-gating, and the Redis rate limiter.

Companion to test_auth_flows.py and test_authorization_and_audit.py — same
real-database-with-rolled-back-transaction pattern; see those modules'
docstrings for the full rationale.

The public endpoints (`GET /api/v1/public/treatments`,
`POST /api/v1/public/booking-requests`) resolve "the" organization via
`OrganizationRepository.get_first()` — correct for this single-tenant
product in production, but in the shared local/dev Postgres instance there
are ~200+ leftover throwaway organizations from before an earlier
test-isolation fix landed (see "Reference and demonstration data" in
missing_features.md), all older than anything a test creates. That means
`get_first()` never resolves to an org a test just registered, so exercising
the *public* endpoints' full request/response cycle against a
test-controlled organization isn't reliable here. The org-boundary logic
those endpoints depend on (BookingRequestService.create_request,
BookingRequestRepository) is tested directly instead, which is both
deterministic and a more precise test of what's actually new — the
get_first()-based org resolution itself is pre-existing, already-relied-on
behavior (seed_reference_data.py, the consent workflows), not something
this feature introduces.
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
from medical_api.core.exceptions import NotFoundError
from medical_api.core.rate_limit import check_rate_limit
from medical_api.main import app
from medical_api.modules.booking.models import BookingRequest
from medical_api.modules.booking.repository import BookingRequestRepository
from medical_api.modules.booking.schemas import BookingRequestCreate
from medical_api.modules.booking.service import BookingRequestService
from medical_api.modules.organizations.models import Organization
from medical_api.modules.treatments.models import TreatmentDefinition
from medical_api.modules.treatments.repository import TreatmentDefinitionRepository

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
        pytest.skip("no reachable database for booking integration tests")


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


async def _make_org(session: AsyncSession) -> Organization:
    organization = Organization(name=f"Direct Org {uuid.uuid4()}")
    session.add(organization)
    await session.flush()
    return organization


async def _make_treatment(
    session: AsyncSession, organization_id: uuid.UUID, *, is_active: bool = True
) -> TreatmentDefinition:
    definition = TreatmentDefinition(
        organization_id=organization_id, name="Facial", is_active=is_active
    )
    session.add(definition)
    await session.flush()
    return definition


def _valid_payload(treatment_definition_id: uuid.UUID) -> BookingRequestCreate:
    return BookingRequestCreate(
        treatment_definition_id=treatment_definition_id,
        first_name="Jane",
        last_name="Doe",
        phone_number="+573001112233",
    )


async def test_create_request_rejects_honeypot_submissions_silently(client):
    session = client.db_session
    org = await _make_org(session)
    treatment = await _make_treatment(session, org.id)
    repository = BookingRequestRepository(session)
    service = BookingRequestService(repository, TreatmentDefinitionRepository(session))

    payload = _valid_payload(treatment.id)
    payload.website = "http://spam.example"

    result = await service.create_request(org.id, payload, ip_address="1.2.3.4")

    assert result is None
    assert await repository.list_all(org.id) == []


async def test_create_request_rejects_cross_org_treatment(client):
    session = client.db_session
    org_a = await _make_org(session)
    org_b = await _make_org(session)
    treatment_in_a = await _make_treatment(session, org_a.id)
    service = BookingRequestService(
        BookingRequestRepository(session), TreatmentDefinitionRepository(session)
    )

    with pytest.raises(NotFoundError):
        await service.create_request(
            org_b.id, _valid_payload(treatment_in_a.id), ip_address="1.2.3.4"
        )


async def test_create_request_rejects_inactive_treatment(client):
    session = client.db_session
    org = await _make_org(session)
    inactive_treatment = await _make_treatment(session, org.id, is_active=False)
    service = BookingRequestService(
        BookingRequestRepository(session), TreatmentDefinitionRepository(session)
    )

    with pytest.raises(NotFoundError):
        await service.create_request(
            org.id, _valid_payload(inactive_treatment.id), ip_address="1.2.3.4"
        )


async def test_create_request_persists_and_is_org_scoped(client):
    session = client.db_session
    org_a = await _make_org(session)
    org_b = await _make_org(session)
    treatment = await _make_treatment(session, org_a.id)
    repository = BookingRequestRepository(session)
    service = BookingRequestService(repository, TreatmentDefinitionRepository(session))

    created = await service.create_request(
        org_a.id, _valid_payload(treatment.id), ip_address="9.9.9.9"
    )

    assert created is not None
    assert created.status == "pending"
    org_a_requests = await repository.list_all(org_a.id)
    assert [r.id for r in org_a_requests] == [created.id]
    assert await repository.list_all(org_b.id) == []


async def test_staff_booking_endpoints_are_role_gated_and_org_scoped(client):
    org_a = await _register_org(client)
    admin_a_headers = {"Authorization": f"Bearer {org_a['access_token']}"}
    org_b = await _register_org(client)
    admin_b_headers = {"Authorization": f"Bearer {org_b['access_token']}"}

    session = client.db_session
    org_a_id = uuid.UUID(org_a["organization_id"])
    treatment_a = await _make_treatment(session, org_a_id)
    booking_a = BookingRequest(
        organization_id=org_a_id,
        treatment_definition_id=treatment_a.id,
        first_name="Jane",
        last_name="Doe",
        phone_number="+573001112233",
    )
    session.add(booking_a)
    await session.flush()

    # Org B's admin must not see org A's booking request.
    org_b_list = await client.get("/api/v1/booking-requests", headers=admin_b_headers)
    assert org_b_list.status_code == 200
    assert org_b_list.json() == []

    org_a_list = await client.get("/api/v1/booking-requests", headers=admin_a_headers)
    assert org_a_list.status_code == 200
    assert [r["id"] for r in org_a_list.json()] == [str(booking_a.id)]

    # A role outside the allowed staff set (auditor is for the audit trail
    # only, not front-desk operations) must be rejected.
    auditor = await _invite_and_accept(client, admin_a_headers, "auditor")
    auditor_headers = {"Authorization": f"Bearer {auditor['access_token']}"}
    forbidden = await client.get("/api/v1/booking-requests", headers=auditor_headers)
    assert forbidden.status_code == 403

    status_update = await client.patch(
        f"/api/v1/booking-requests/{booking_a.id}/status",
        json={"status": "contacted"},
        headers=admin_a_headers,
    )
    assert status_update.status_code == 200
    assert status_update.json()["status"] == "contacted"

    # Recorded in the audit trail, matching every other staff mutation.
    audit_events = await client.get("/api/v1/audit", headers=admin_a_headers)
    actions = [e["action"] for e in audit_events.json()]
    assert "booking_request.status_updated" in actions

    # Org B still can't touch org A's booking request by ID.
    cross_org_update = await client.patch(
        f"/api/v1/booking-requests/{booking_a.id}/status",
        json={"status": "declined"},
        headers=admin_b_headers,
    )
    assert cross_org_update.status_code == 404


async def test_public_treatments_endpoint_is_reachable_without_auth(client):
    response = await client.get("/api/v1/public/treatments")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


async def test_rate_limit_allows_up_to_the_limit_then_blocks(client):
    key = f"test:{uuid.uuid4()}"
    for _ in range(5):
        assert await check_rate_limit(key, limit=5, window_seconds=60) is True
    assert await check_rate_limit(key, limit=5, window_seconds=60) is False
