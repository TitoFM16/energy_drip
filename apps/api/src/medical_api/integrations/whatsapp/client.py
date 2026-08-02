"""Thin client for the WhatsApp Business Cloud API.

The API layer only enqueues outbox events (see
`medical_api.modules.notifications.service.enqueue_event`); actual delivery
runs in `apps/worker` so a slow/unavailable provider never blocks a request.
This client is shared by the worker's `send_whatsapp` activity.

This product's only outbound notification channel is WhatsApp, called
directly against Meta's Cloud API (no BSP middleman) — see the
"Product scope correction" notes in docs/missing_features.md.
"""

import httpx

from medical_api.core.config import get_settings


class WhatsAppNotConfiguredError(Exception):
    """WHATSAPP_API_TOKEN / WHATSAPP_PHONE_NUMBER_ID aren't set.

    Not retryable: every retry would fail identically. Callers should log
    and give up rather than let a retry policy burn through attempts (and
    hammer Meta's API with an empty bearer token) for a guaranteed failure.
    """


class WhatsAppRejectedError(Exception):
    """Meta rejected the request outright (bad/unapproved template name,
    invalid recipient number, expired or revoked token, malformed payload).

    Not retryable: the same request produces the same 4xx on every retry.
    """


class WhatsAppTransientError(Exception):
    """Rate limited (429), a Meta-side server error (5xx), or a network
    failure reaching the API. Retryable — the caller's retry/backoff policy
    should handle this like any other transient failure.
    """


class WhatsAppClient:
    def __init__(self) -> None:
        settings = get_settings()
        self._token = settings.whatsapp_api_token
        self._phone_number_id = settings.whatsapp_phone_number_id
        self._base_url = f"https://graph.facebook.com/v20.0/{self._phone_number_id}/messages"

    async def send_template_message(self, to: str, template_name: str, params: list[str]) -> str:
        if not self._token or not self._phone_number_id:
            raise WhatsAppNotConfiguredError(
                "WHATSAPP_API_TOKEN / WHATSAPP_PHONE_NUMBER_ID are not configured."
            )

        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": "es"},
                "components": [
                    {"type": "body", "parameters": [{"type": "text", "text": p} for p in params]}
                ],
            },
        }
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self._base_url,
                    json=payload,
                    headers={"Authorization": f"Bearer {self._token}"},
                    timeout=10.0,
                )
            except httpx.TransportError as exc:
                raise WhatsAppTransientError(
                    f"Network error calling the WhatsApp API: {exc}"
                ) from exc

        if response.status_code == 429 or response.status_code >= 500:
            raise WhatsAppTransientError(
                f"WhatsApp API returned a transient error ({response.status_code}): {response.text}"
            )
        if response.status_code >= 400:
            raise WhatsAppRejectedError(
                f"WhatsApp API rejected the message ({response.status_code}): {response.text}"
            )
        return response.json()["messages"][0]["id"]
