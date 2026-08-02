import hashlib
import secrets


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


def generate_opaque_token() -> tuple[str, str]:
    """Returns (raw_token, token_hash). Only the hash is ever persisted —
    the raw token is the caller's responsibility to deliver out-of-band
    (URL, WhatsApp, response body in dev) and never store.
    """
    raw_token = secrets.token_urlsafe(32)
    return raw_token, hash_token(raw_token)
