"""Per-request context (request ID, client IP, user agent) available without
threading a `Request` parameter through every route and service that needs
it — chiefly `AuditService`, which needs this on nearly every mutating
endpoint across every module. Set once per request by `RequestContextMiddleware`.
"""

from contextvars import ContextVar, Token
from dataclasses import dataclass

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_ip_address: ContextVar[str | None] = ContextVar("ip_address", default=None)
_user_agent: ContextVar[str | None] = ContextVar("user_agent", default=None)


@dataclass(frozen=True)
class _Tokens:
    request_id: Token[str | None]
    ip_address: Token[str | None]
    user_agent: Token[str | None]


def bind_request_context(
    *, request_id: str, ip_address: str | None, user_agent: str | None
) -> _Tokens:
    return _Tokens(
        request_id=_request_id.set(request_id),
        ip_address=_ip_address.set(ip_address),
        user_agent=_user_agent.set(user_agent),
    )


def reset_request_context(tokens: _Tokens) -> None:
    _request_id.reset(tokens.request_id)
    _ip_address.reset(tokens.ip_address)
    _user_agent.reset(tokens.user_agent)


def get_request_id() -> str | None:
    return _request_id.get()


def get_ip_address() -> str | None:
    return _ip_address.get()


def get_user_agent() -> str | None:
    return _user_agent.get()
