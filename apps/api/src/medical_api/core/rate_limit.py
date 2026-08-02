from redis.asyncio import Redis

from medical_api.core.config import get_settings

settings = get_settings()
_redis: Redis | None = None


def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def check_rate_limit(key: str, *, limit: int, window_seconds: int) -> bool:
    """Fixed-window counter. Returns True if this call is within `limit`
    requests for the current `window_seconds`-long window, False once the
    caller has exceeded it.

    Fixed-window (not sliding/token-bucket) is a deliberate simplification:
    it lets a caller burst up to ~2x limit across a window boundary, which
    is an acceptable trade for the one place this is used today (the
    public booking form) given the low absolute limits involved.
    """
    redis = get_redis()
    current = await redis.incr(key)
    if current == 1:
        await redis.expire(key, window_seconds)
    return current <= limit
