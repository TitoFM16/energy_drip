"""Thin SMS provider client (Twilio-shaped). Swap the base URL/payload for
whichever provider is chosen without touching calling code in the worker.
"""

import httpx

from medical_api.core.config import get_settings


class SmsClient:
    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.sms_provider_api_key

    async def send(self, to: str, body: str) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.sms-provider.example.com/v1/messages",
                json={"to": to, "body": body},
                headers={"Authorization": f"Bearer {self._api_key}"},
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json()["id"]
