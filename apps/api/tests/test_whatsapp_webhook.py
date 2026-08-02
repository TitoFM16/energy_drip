import hashlib
import hmac

from medical_api.integrations.whatsapp.webhook import extract_status_updates, verify_signature

APP_SECRET = "test-app-secret"


def _sign(body: bytes, secret: str = APP_SECRET) -> str:
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def _status_payload(*statuses: dict) -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "waba-id",
                "changes": [{"value": {"statuses": list(statuses)}, "field": "messages"}],
            }
        ],
    }


class TestVerifySignature:
    def test_accepts_a_correctly_signed_body(self):
        body = b'{"hello": "world"}'
        assert verify_signature(body, _sign(body), APP_SECRET) is True

    def test_rejects_a_body_signed_with_the_wrong_secret(self):
        body = b'{"hello": "world"}'
        assert verify_signature(body, _sign(body, secret="wrong-secret"), APP_SECRET) is False

    def test_rejects_a_tampered_body(self):
        body = b'{"hello": "world"}'
        signature = _sign(body)
        tampered = b'{"hello": "mallory"}'
        assert verify_signature(tampered, signature, APP_SECRET) is False

    def test_rejects_a_missing_signature_header(self):
        assert verify_signature(b"{}", None, APP_SECRET) is False

    def test_rejects_a_signature_missing_the_sha256_prefix(self):
        body = b"{}"
        digest = hmac.new(APP_SECRET.encode(), body, hashlib.sha256).hexdigest()
        assert verify_signature(body, digest, APP_SECRET) is False

    def test_rejects_when_no_app_secret_is_configured(self):
        # Matches WhatsAppClient's own fail-safe: an empty secret must never
        # be treated as "anything verifies", or an unconfigured deployment
        # would silently accept unsigned/unverifiable webhook calls.
        body = b"{}"
        assert verify_signature(body, _sign(body, secret=""), "") is False


class TestExtractStatusUpdates:
    def test_extracts_a_single_sent_status(self):
        payload = _status_payload({"id": "wamid.123", "status": "sent"})
        updates = extract_status_updates(payload)
        assert updates == [
            {"provider_message_id": "wamid.123", "status": "sent", "failure_reason": None}
        ]

    def test_maps_read_to_delivered(self):
        payload = _status_payload({"id": "wamid.123", "status": "read"})
        updates = extract_status_updates(payload)
        assert updates[0]["status"] == "delivered"

    def test_extracts_failure_reason_from_a_failed_status(self):
        payload = _status_payload(
            {
                "id": "wamid.123",
                "status": "failed",
                "errors": [{"code": 131047, "title": "Message failed to send"}],
            }
        )
        updates = extract_status_updates(payload)
        assert updates[0]["status"] == "failed"
        assert updates[0]["failure_reason"] == "Message failed to send"

    def test_handles_multiple_statuses_across_multiple_entries(self):
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "waba-1",
                    "changes": [
                        {
                            "value": {
                                "statuses": [
                                    {"id": "wamid.1", "status": "sent"},
                                    {"id": "wamid.2", "status": "delivered"},
                                ]
                            },
                            "field": "messages",
                        }
                    ],
                },
                {
                    "id": "waba-2",
                    "changes": [{"value": {"statuses": [{"id": "wamid.3", "status": "failed"}]}}],
                },
            ],
        }
        updates = extract_status_updates(payload)
        assert [u["provider_message_id"] for u in updates] == ["wamid.1", "wamid.2", "wamid.3"]

    def test_skips_an_entry_missing_a_message_id(self):
        payload = _status_payload({"status": "sent"})
        assert extract_status_updates(payload) == []

    def test_skips_an_entry_with_an_unrecognized_status(self):
        payload = _status_payload({"id": "wamid.123", "status": "some_future_status"})
        assert extract_status_updates(payload) == []

    def test_returns_an_empty_list_for_a_payload_with_no_statuses(self):
        assert extract_status_updates({"object": "whatsapp_business_account", "entry": []}) == []

    def test_ignores_a_completely_unrelated_payload_shape(self):
        assert extract_status_updates({}) == []
