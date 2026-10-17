"""Small fixed-window limiter for the MVP's single API process.

Counters reset on restart. Run exactly one API worker; horizontal scaling
requires a shared limiter before adding replicas.
"""

from time import monotonic

_windows: dict[str, tuple[float, int]] = {}
_MAX_KEYS = 10_000


async def check_rate_limit(key: str, *, limit: int, window_seconds: int) -> bool:
    # No awaits between read/write: this operation is atomic on the API event loop.
    now = monotonic()
    expires_at, count = _windows.get(key, (now + window_seconds, 0))
    if expires_at <= now:
        expires_at, count = now + window_seconds, 0
    if key not in _windows and len(_windows) >= _MAX_KEYS:
        for expired_key in [k for k, (expires, _) in _windows.items() if expires <= now]:
            del _windows[expired_key]
        if len(_windows) >= _MAX_KEYS:
            # Refuse new keys rather than evicting active limits under load.
            return False
    count += 1
    _windows[key] = (expires_at, count)
    return count <= limit
