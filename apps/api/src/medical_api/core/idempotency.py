"""Idempotency-key support for mutating endpoints that may be retried by
flaky mobile networks (notably the patient consent submission flow).
"""

import hashlib


def fingerprint(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()
