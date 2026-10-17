"""Render a signed consent without fetching external or local resources."""

from datetime import datetime
from html import escape
from typing import Any

from weasyprint import HTML

from medical_api.shared.utilities.hashing import sha256_hash

__all__ = ["render_consent_pdf", "sha256_hash"]


def _deny_resource(url: str, **kwargs):
    raise ValueError("External PDF resources are disabled")


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
        f"<tr><td>{escape(str(a['field_key']))}</td><td>{escape(str(a['value']))}</td></tr>"
        for a in answers
    )
    html = f"""
    <html lang="es"><head><meta charset="utf-8"><style>
    @page {{ size: A4; margin: 20mm; }}
    body {{ font-family: sans-serif; font-size: 11pt; color: #17242a; }}
    .consent {{ white-space: pre-wrap; line-height: 1.5; }}
    td {{ padding: 6px; border-bottom: 1px solid #ddd; }}
    svg {{ max-width: 100%; height: 120px; }}
    </style></head><body>
    <h1>Consentimiento informado</h1>
    <p>Paciente: {escape(patient_name)}</p>
    <div class="consent">{escape(template_body_markdown)}</div>
    <table>{answer_rows}</table>
    <p>Firmado: {escape(signed_at.isoformat())} · IP: {escape(ip_address)}</p>
    <div>{signature_svg}</div>
    </body></html>
    """
    return HTML(string=html, url_fetcher=_deny_resource).write_pdf()
