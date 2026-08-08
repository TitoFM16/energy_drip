"""Sanitizes patient-submitted signature SVGs before storage/PDF embedding.

The real signature payload (see apps/patient-web's signature-pad component)
is always `<svg><image href="data:image/png;base64,..."/></svg>` — a canvas
export, not hand-authored markup. Anything else is treated as hostile input
from an unauthenticated public endpoint. The biggest concrete risk is SSRF:
an `<image href="http://169.254.169.254/...">` or a Docker-internal hostname
would get fetched server-side when WeasyPrint renders the PDF, so `href`
values are restricted to `data:image/...;base64,` URIs only. A handful of
harmless vector tags are also allowed in case a future signature widget
switches to path-based export instead of a PNG data URI.
"""

import re
from xml.etree import ElementTree

from defusedxml.ElementTree import fromstring as safe_fromstring

MAX_SVG_LENGTH = 2_000_000

_DATA_IMAGE_URI = re.compile(r"^data:image/(png|jpeg|jpg);base64,[A-Za-z0-9+/]+=*$")

_ALLOWED_TAGS = {
    "svg",
    "image",
    "path",
    "g",
    "line",
    "polyline",
    "polygon",
    "rect",
    "circle",
    "ellipse",
}

_ALLOWED_ATTRS = {
    "svg": {"xmlns", "width", "height", "viewBox", "version"},
    "image": {"href", "x", "y", "width", "height", "preserveAspectRatio"},
    "path": {
        "d",
        "fill",
        "stroke",
        "stroke-width",
        "stroke-linecap",
        "stroke-linejoin",
        "transform",
    },
    "g": {"transform", "fill", "stroke"},
    "line": {"x1", "y1", "x2", "y2", "stroke", "stroke-width"},
    "polyline": {"points", "fill", "stroke", "stroke-width"},
    "polygon": {"points", "fill", "stroke", "stroke-width"},
    "rect": {"x", "y", "width", "height", "rx", "ry", "fill", "stroke"},
    "circle": {"cx", "cy", "r", "fill", "stroke"},
    "ellipse": {"cx", "cy", "rx", "ry", "fill", "stroke"},
}


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _sanitize_element(element: ElementTree.Element) -> None:
    tag = _local_name(element.tag)
    if tag not in _ALLOWED_TAGS:
        raise ValueError(f"Disallowed SVG element: {tag}")

    allowed_attrs = _ALLOWED_ATTRS[tag]
    for key in list(element.attrib):
        local_key = _local_name(key)
        if local_key not in allowed_attrs:
            raise ValueError(f"Disallowed SVG attribute on <{tag}>: {local_key}")
        if key != local_key:
            # Drop any namespaced attribute (e.g. legacy xlink:href) in
            # favor of a plain attribute name — never trust a namespaced
            # value we haven't explicitly validated below.
            raise ValueError(f"Disallowed namespaced SVG attribute on <{tag}>: {key}")

    if tag == "image":
        href = element.attrib.get("href", "")
        if not _DATA_IMAGE_URI.match(href):
            raise ValueError("<image> href must be a data:image/... base64 URI")

    for child in element:
        _sanitize_element(child)


def sanitize_signature_svg(raw_svg: str) -> str:
    """Returns a re-serialized, safe-to-embed SVG. Raises ValueError with a
    human-readable reason if `raw_svg` is not a well-formed, allowlisted SVG.
    """
    if not raw_svg or len(raw_svg) > MAX_SVG_LENGTH:
        raise ValueError("Signature SVG is missing or exceeds the maximum allowed size")

    try:
        # defusedxml rejects DOCTYPE/ENTITY declarations, external entity
        # references, and other XXE/billion-laughs vectors before this ever
        # reaches the stdlib parser.
        root = safe_fromstring(raw_svg)
    except ElementTree.ParseError as exc:
        raise ValueError(f"Signature SVG is not well-formed XML: {exc}") from exc

    if _local_name(root.tag) != "svg":
        raise ValueError("Signature SVG must have an <svg> root element")

    _sanitize_element(root)
    return ElementTree.tostring(root, encoding="unicode")
