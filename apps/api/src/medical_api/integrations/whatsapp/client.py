"""Thin client for the WhatsApp Business Cloud API.

The API layer only enqueues outbox events (see
`medical_api.modules.notifications.service.enqueue_event`); actual delivery
runs in `apps/worker` so a slow/unavailable provider never blocks a request.
This client is shared by the worker's `send_whatsapp` activity.
"""

import httpx

from medical_api.core.config import get_settings


class WhatsAppClient:
    def __init__(self) -> None:
        settings = get_settings()
        self._token = settings.whatsapp_api_token
        self._phone_number_id = settings.whatsapp_phone_number_id
        self._base_url = f"https://graph.facebook.com/v20.0/{self._phone_number_id}/messages"

    async def send_template_message(self, to: str, template_name: str, params: list[str]) -> str:
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
            response = await client.post(
                self._base_url,
                json=payload,
                headers={"Authorization": f"Bearer {self._token}"},
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json()["messages"][0]["id"]
