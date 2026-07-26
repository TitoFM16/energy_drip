"""Renders a consent submission into an immutable PDF byte stream.

Called from the worker's `generate_pdf` activity after a `consent.submitted`
outbox event (see docs/architecture). Requires the `medical-api[pdf]` extra
(WeasyPrint) which only `apps/worker` installs.
"""

import hashlib
from datetime import datetime
from typing import Any

from weasyprint import HTML


def render_consent_pdf(
    *,
    patient_name: str,
    template_body_markdown: str,
    answers: list[dict[str, Any]],
    signature_svg: str,
    signed_at: datetime,
    ip_address: str,
) -> bytes:
    answer_rows = "".join(
        f"<tr><td>{a['field_key']}</td><td>{a['value']}</td></tr>" for a in answers
    )
    html = f"""
    <html><body>
      <h1>Consentimiento informado</h1>
      <p>Paciente: {patient_name}</p>
      <div>{template_body_markdown}</div>
      <table>{answer_rows}</table>
      <p>Firmado: {signed_at.isoformat()} &middot; IP: {ip_address}</p>
      <div>{signature_svg}</div>
    </body></html>
    """
    return HTML(string=html).write_pdf()


def sha256_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
