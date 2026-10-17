"""Storage boundaries and rendering needed for the queue-free MVP."""

import io
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

import pytest
from jose import jwt
from PIL import Image

from medical_api.core import rate_limit
from medical_api.core.config import Settings
from medical_api.integrations.object_storage import client as storage
from medical_api.integrations.pdf.generator import render_consent_pdf
from medical_api.modules.treatments.images import store_service_image


@pytest.fixture
def local_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(storage.settings, "storage_backend", "local")
    monkeypatch.setattr(storage.settings, "private_storage_path", tmp_path / "private")
    monkeypatch.setattr(storage.settings, "public_media_path", tmp_path / "media")
    return tmp_path


def test_private_storage_is_immutable_and_download_token_expires(local_storage):
    storage.upload_bytes("org/a.pdf", b"%PDF-record", "application/pdf")
    assert storage.download_bytes("org/a.pdf") == b"%PDF-record"
    with pytest.raises(FileExistsError):
        storage.upload_bytes("org/a.pdf", b"changed", "application/pdf")
    with pytest.raises(ValueError):
        storage.upload_bytes("../outside.pdf", b"bad", "application/pdf")
    token = urlparse(storage.generate_presigned_download_url("org/a.pdf")).path.rsplit("/", 1)[1]
    assert storage.resolve_download_token(token) == "org/a.pdf"
    expired = jwt.encode(
        {
            "key": "org/a.pdf",
            "aud": "consent-download",
            "exp": datetime.now(UTC) - timedelta(seconds=1),
        },
        storage.settings.secret_key,
        algorithm=storage.settings.algorithm,
    )
    with pytest.raises(ValueError):
        storage.resolve_download_token(expired)
    with pytest.raises(ValueError):
        storage.resolve_download_token(token + "tampered")


def test_service_image_is_resized_reencoded_and_private_files_are_separate(local_storage):
    original = io.BytesIO()
    Image.new("RGB", (2000, 1000), "red").save(original, format="PNG")
    url = store_service_image(original.getvalue())
    assert url.startswith("/media/services/")
    image = Image.open(local_storage / url.removeprefix("/"))
    assert image.format == "WEBP"
    assert image.size == (1600, 800)
    with pytest.raises(ValueError):
        store_service_image(b"<svg><script>alert(1)</script></svg>")


def test_pdf_contains_real_pdf_and_does_not_fetch_patient_supplied_html():
    pdf = render_consent_pdf(
        patient_name="Paciente <script>test</script>",
        template_body_markdown='<img src="file:///etc/passwd"> Consentimiento',
        answers=[{"field_key": "alergias", "value": "<b>ninguna</b>"}],
        signature_svg=(
            '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="60">'
            '<path d="M10 10 L80 40" stroke="black"/></svg>'
        ),
        signed_at=datetime.now(UTC),
        ip_address="127.0.0.1",
    )
    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 1000


async def test_rate_limiter_resets_expired_window_without_redis(monkeypatch):
    monkeypatch.setattr(rate_limit, "_windows", {})
    monkeypatch.setattr(rate_limit, "monotonic", lambda: 100.0)
    assert await rate_limit.check_rate_limit("ip", limit=1, window_seconds=10)
    assert not await rate_limit.check_rate_limit("ip", limit=1, window_seconds=10)
    monkeypatch.setattr(rate_limit, "monotonic", lambda: 111.0)
    assert await rate_limit.check_rate_limit("ip", limit=1, window_seconds=10)


def test_production_rejects_default_secrets_and_accepts_explicit_settings():
    with pytest.raises(ValueError):
        Settings(environment="production", allowed_hosts=["clinic.example.com"])
    configured = Settings(
        environment="production",
        secret_key="a" * 64,
        allowed_hosts=["clinic.example.com"],
        public_organization_id="",
    )
    assert configured.storage_backend == "local"
    assert configured.public_organization_id is None


def test_s3_backend_uses_private_objects_and_presigned_downloads(monkeypatch):
    class StorageClient:
        def __init__(self):
            self.objects = {}

        def put_object(self, *, Bucket, Key, Body, ContentType):  # noqa: N803
            self.objects[(Bucket, Key)] = Body
            assert ContentType == "application/pdf"

        def get_object(self, *, Bucket, Key):  # noqa: N803
            return {"Body": io.BytesIO(self.objects[(Bucket, Key)])}

        def generate_presigned_url(self, operation, *, Params, ExpiresIn):  # noqa: N803
            assert operation == "get_object"
            assert ExpiresIn == 300
            assert Params["Key"] == "org/a.pdf"
            return "https://storage.example.com/private-signed-download"

    fake = StorageClient()
    monkeypatch.setattr(storage.settings, "storage_backend", "s3")
    monkeypatch.setattr(storage, "get_s3_client", lambda: fake)
    monkeypatch.setattr(storage, "get_s3_public_client", lambda: fake)
    storage.upload_bytes("org/a.pdf", b"%PDF-s3", "application/pdf")
    assert storage.download_bytes("org/a.pdf") == b"%PDF-s3"
    assert storage.generate_presigned_download_url("org/a.pdf").startswith("https://storage.")
    configured = Settings(s3_endpoint_url="", s3_access_key="", s3_secret_key="")
    assert configured.s3_endpoint_url is None
    assert configured.s3_access_key is None
