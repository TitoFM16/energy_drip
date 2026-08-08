import hmac
from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, HTTPException, Query, Request, Response, status

from medical_api.api.dependencies import DbSession
from medical_api.core.config import get_settings
from medical_api.integrations.whatsapp.webhook import (
    extract_inbound_messages,
    extract_status_updates,
    is_opt_out_message,
    verify_signature,
)
from medical_api.modules.audit.service import AuditService
from medical_api.modules.notifications.service import enqueue_event
from medical_api.modules.organizations.repository import OrganizationRepository
from medical_api.modules.patients.repository import PatientRepository

logger = structlog.get_logger(__name__)
settings = get_settings()

# Mounted at /api/v1/webhooks/whatsapp. Unauthenticated in the JWT sense —
# Meta can't send a Bearer token — but every POST is verified against the
# App Secret's HMAC signature below, which is the actual authentication
# mechanism for this route.
public_router = APIRouter()


@public_router.get("")
async def verify_whatsapp_webhook(
    hub_mode: str = Query(alias="hub.mode"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge"),
) -> Response:
    """The handshake Meta performs once, when a webhook URL is registered
    or re-verified in the App Dashboard: it must get its own `hub.challenge`
    value echoed back, and only if `hub.verify_token` matches the value
    configured on both sides.
    """
    token_matches = hmac.compare_digest(hub_verify_token, settings.whatsapp_webhook_verify_token)
    if hub_mode != "subscribe" or not token_matches:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid verify token")
    return Response(content=hub_challenge, media_type="text/plain")


@public_router.post("")
async def receive_whatsapp_webhook(request: Request, session: DbSession) -> dict[str, str]:
    """Verifies the signature, then enqueues one outbox event per status
    update in the batch rather than processing them inline — matching this
    app's existing rule that the API layer only ever enqueues work, never
    calls an external system or does non-trivial processing synchronously.
    Always returns 200 once the signature check passes (even for payloads
    with nothing useful in them): Meta retries non-2xx responses, and a
    malformed-but-signed entry retried forever wouldn't become parseable on
    a later attempt.
    """
    raw_body = await request.body()
    signature = request.headers.get("x-hub-signature-256")
    if not verify_signature(raw_body, signature, settings.whatsapp_app_secret):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid signature")

    try:
        payload = await request.json()
    except ValueError:
        logger.warning("whatsapp_webhook.invalid_json")
        return {"status": "ignored"}

    updates = extract_status_updates(payload)
    opt_out_messages = [
        message
        for message in extract_inbound_messages(payload)
        if is_opt_out_message(message["body"])
    ]
    if updates or opt_out_messages:
        # This webhook is scoped by Meta's WhatsApp Business Account, not
        # by our own organization_id — but this product has exactly one
        # organization (see docs/missing_features.md's single-clinic scope
        # decision), so resolving "the" organization here is correct rather
        # than a shortcut.
        organization = await OrganizationRepository(session).get_first()
        if organization is not None:
            for update in updates:
                await enqueue_event(
                    session,
                    organization_id=organization.id,
                    event_type="whatsapp.delivery_status",
                    payload=dict(update),
                )
            processed_patients: set[str] = set()
            patient_repository = PatientRepository(session)
            for message in opt_out_messages:
                patient = await patient_repository.get_by_phone_number(
                    organization.id, message["sender_phone_number"]
                )
                if (
                    patient is None
                    or patient.whatsapp_opt_out
                    or str(patient.id) in processed_patients
                ):
                    continue
                patient.whatsapp_opt_out = True
                patient.whatsapp_opt_out_at = datetime.now(UTC)
                processed_patients.add(str(patient.id))
                await AuditService(session).record(
                    organization_id=organization.id,
                    actor_user_id=None,
                    action="patient.whatsapp_opt_out",
                    resource_type="patient",
                    resource_id=str(patient.id),
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent"),
                    metadata={"provider_message_id": message["provider_message_id"]},
                )
            await session.commit()

    return {"status": "received"}
