"""Coverage for "Strict submission validation" (P0) in missing_features.md:
the public, unauthenticated `/consents/{token}/submit` endpoint must reject
answers that don't match the template version's real questions, and must
sanitize the signature SVG rather than trust it verbatim. Same
real-database-plus-savepoint pattern as test_consent_lifecycle.py — see that
module's docstring for the full rationale.
"""

import base64
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

# A 1x1 transparent PNG, base64-encoded — a realistic stand-in for the
# canvas.toDataURL() output apps/patient-web's SignaturePad produces.
_VALID_SIGNATURE_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="340" height="180">'
    '<image href="data:image/png;base64,'
    + base64.b64encode(b"\x89PNG\r\n\x1a\n").decode()
    + '" width="340" height="180" /></svg>'
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
        pytest.skip("no reachable database for submission-validation integration tests")


async def _register_org(client) -> dict:
    response = await client.post(
        "/api/v1/auth/register-organization",
        json={
            "organization_name": f"Validation Clinic {uuid.uuid4()}",
            "admin_email": f"validation-{uuid.uuid4()}@example.com",
            "admin_password": "supersecret123",
            "admin_full_name": "Validation Admin",
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


async def _published_template_version(client, headers: dict) -> str:
    template = await client.post(
        "/api/v1/consents/templates",
        json={
            "name": f"Consent {uuid.uuid4()}",
            "body_markdown": "Consiento el tratamiento.",
            "questions": [
                {
                    "field_key": "is_pregnant",
                    "prompt": "¿Está embarazada?",
                    "question_type": "boolean",
                    "display_order": 0,
                    "is_required": True,
                },
                {
                    "field_key": "skin_type",
                    "prompt": "Tipo de piel",
                    "question_type": "single_choice",
                    "display_order": 1,
                    "is_required": True,
                    "options": [
                        {"value": "oily", "label": "Grasa"},
                        {"value": "dry", "label": "Seca"},
                    ],
                },
                {
                    "field_key": "notes",
                    "prompt": "Notas adicionales",
                    "question_type": "text",
                    "display_order": 2,
                    "is_required": False,
                },
            ],
        },
        headers=headers,
    )
    assert template.status_code == 201, template.text
    version_id = template.json()["latest_version"]["id"]
    template_id = template.json()["id"]
    publish = await client.post(
        f"/api/v1/consents/templates/{template_id}/versions/{version_id}/publish",
        headers=headers,
    )
    assert publish.status_code == 200, publish.text
    return version_id


async def _create_request(client, headers: dict, patient_id: str, version_id: str) -> dict:
    response = await client.post(
        f"/api/v1/consents/requests?patient_id={patient_id}&template_version_id={version_id}",
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _setup_with_form(client) -> dict:
    org = await _register_org(client)
    headers = {"Authorization": f"Bearer {org['access_token']}"}
    patient_id = await _create_patient(client, headers)
    version_id = await _published_template_version(client, headers)
    request = await _create_request(client, headers, patient_id, version_id)

    form = await client.get(f"/api/v1/public/consents/{request['token']}")
    assert form.status_code == 200, form.text
    questions_by_field = {q["field_key"]: q for q in form.json()["questions"]}
    return {
        "headers": headers,
        "token": request["token"],
        "questions_by_field": questions_by_field,
    }


def _valid_answers(questions_by_field: dict) -> list[dict]:
    return [
        {
            "question_id": questions_by_field["is_pregnant"]["id"],
            "field_key": "is_pregnant",
            "value": False,
        },
        {
            "question_id": questions_by_field["skin_type"]["id"],
            "field_key": "skin_type",
            "value": "oily",
        },
    ]


async def _submit(
    client, token: str, answers: list[dict], signature_svg: str = _VALID_SIGNATURE_SVG
):
    return await client.post(
        f"/api/v1/public/consents/{token}/submit",
        json={"answers": answers, "signature_svg": signature_svg, "timezone": "America/Bogota"},
    )


async def test_valid_submission_succeeds(client):
    ctx = await _setup_with_form(client)
    response = await _submit(client, ctx["token"], _valid_answers(ctx["questions_by_field"]))
    assert response.status_code == 201, response.text


async def test_unknown_question_id_is_rejected(client):
    ctx = await _setup_with_form(client)
    answers = _valid_answers(ctx["questions_by_field"])
    answers.append({"question_id": str(uuid.uuid4()), "field_key": "bogus", "value": "x"})

    response = await _submit(client, ctx["token"], answers)
    assert response.status_code == 400, response.text
    assert response.json()["detail"]["reason"] == "unknown_question"


async def test_missing_required_answer_is_rejected(client):
    ctx = await _setup_with_form(client)
    answers = [
        a for a in _valid_answers(ctx["questions_by_field"]) if a["field_key"] != "skin_type"
    ]

    response = await _submit(client, ctx["token"], answers)
    assert response.status_code == 400, response.text
    assert response.json()["detail"]["reason"] == "missing_required_answer"


async def test_field_key_mismatch_is_rejected(client):
    ctx = await _setup_with_form(client)
    answers = _valid_answers(ctx["questions_by_field"])
    answers[0]["field_key"] = "not_the_real_field_key"

    response = await _submit(client, ctx["token"], answers)
    assert response.status_code == 400, response.text
    assert response.json()["detail"]["reason"] == "field_key_mismatch"


async def test_wrong_value_type_for_boolean_question_is_rejected(client):
    ctx = await _setup_with_form(client)
    answers = _valid_answers(ctx["questions_by_field"])
    answers[0]["value"] = "not-a-boolean"

    response = await _submit(client, ctx["token"], answers)
    assert response.status_code == 400, response.text
    assert response.json()["detail"]["reason"] == "invalid_answer_value"


async def test_single_choice_value_outside_declared_options_is_rejected(client):
    ctx = await _setup_with_form(client)
    answers = _valid_answers(ctx["questions_by_field"])
    answers[1]["value"] = "some-option-that-does-not-exist"

    response = await _submit(client, ctx["token"], answers)
    assert response.status_code == 400, response.text
    assert response.json()["detail"]["reason"] == "invalid_answer_value"


async def test_duplicate_answer_for_same_question_is_rejected(client):
    ctx = await _setup_with_form(client)
    answers = _valid_answers(ctx["questions_by_field"])
    answers.append(dict(answers[0]))

    response = await _submit(client, ctx["token"], answers)
    assert response.status_code == 400, response.text
    assert response.json()["detail"]["reason"] == "duplicate_answer"


async def test_malicious_signature_svg_is_rejected(client):
    ctx = await _setup_with_form(client)
    # An SSRF attempt: fetching an internal/attacker-controlled URL
    # server-side when the worker later renders this into a PDF.
    malicious_svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10">'
        '<image href="http://169.254.169.254/latest/meta-data/" width="10" height="10" />'
        "</svg>"
    )

    response = await _submit(
        client, ctx["token"], _valid_answers(ctx["questions_by_field"]), signature_svg=malicious_svg
    )
    assert response.status_code == 400, response.text
    assert response.json()["detail"]["reason"] == "invalid_signature"


async def test_signature_svg_with_script_tag_is_rejected(client):
    ctx = await _setup_with_form(client)
    malicious_svg = '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'

    response = await _submit(
        client, ctx["token"], _valid_answers(ctx["questions_by_field"]), signature_svg=malicious_svg
    )
    assert response.status_code == 400, response.text
    assert response.json()["detail"]["reason"] == "invalid_signature"


async def test_second_submission_of_same_token_is_rejected(client):
    ctx = await _setup_with_form(client)
    first = await _submit(client, ctx["token"], _valid_answers(ctx["questions_by_field"]))
    assert first.status_code == 201, first.text

    second = await _submit(client, ctx["token"], _valid_answers(ctx["questions_by_field"]))
    assert second.status_code == 410, second.text
    assert second.json()["detail"]["reason"] == "completed"
