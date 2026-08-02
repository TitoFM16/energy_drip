"""Verification and parsing for Meta's WhatsApp Cloud API webhook.

Two independent concerns live here, both pure and easily unit-testable
without live Meta credentials:

- `verify_signature`: confirms an inbound POST really came from Meta (HMAC
  over the raw body using the App Secret — a different secret from the
  access token used to *send* messages).
- `extract_status_updates`: normalizes Meta's nested, batchable webhook
  payload shape into a flat list of status updates the rest of the app can
  act on without knowing Meta's wire format.
"""

import hashlib
import hmac
from typing import Any, TypedDict

# Meta's message-status values, mapped to this app's own NotificationStatus.
# "read" collapses to "delivered" — this product doesn't track read
# receipts separately (see docs/missing_features.md).
_STATUS_MAP = {
    "sent": "sent",
    "delivered": "delivered",
    "read": "delivered",
    "failed": "failed",
}


class StatusUpdate(TypedDict):
    provider_message_id: str
    status: str  # one of NotificationStatus's values
    failure_reason: str | None


def verify_signature(raw_body: bytes, signature_header: str | None, app_secret: str) -> bool:
    """`signature_header` is the raw `X-Hub-Signature-256` header value,
    shaped `sha256=<hex digest>`. Verifies over the exact raw request
    bytes — re-serializing parsed JSON before verifying would silently
    break this, since byte-for-byte formatting isn't guaranteed to survive
    a parse/re-encode round trip.
    """
    if not signature_header or not app_secret:
        return False
    prefix = "sha256="
    if not signature_header.startswith(prefix):
        return False
    expected = hmac.new(app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header[len(prefix) :])


def extract_status_updates(payload: dict[str, Any]) -> list[StatusUpdate]:
    """Walks `entry[].changes[].value.statuses[]`, skipping anything
    malformed rather than raising — a single bad entry in a batch shouldn't
    make the whole webhook call fail (Meta would just retry the same batch,
    including whatever made this entry unparseable, forever).
    """
    updates: list[StatusUpdate] = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            for status_event in change.get("value", {}).get("statuses", []):
                message_id = status_event.get("id")
                raw_status = status_event.get("status")
                mapped_status = _STATUS_MAP.get(raw_status)
                if not message_id or mapped_status is None:
                    continue
                failure_reason = None
                if mapped_status == "failed":
                    errors = status_event.get("errors") or []
                    if errors:
                        first = errors[0]
                        failure_reason = first.get("title") or first.get("message")
                updates.append(
                    StatusUpdate(
                        provider_message_id=message_id,
                        status=mapped_status,
                        failure_reason=failure_reason,
                    )
                )
    return updates
