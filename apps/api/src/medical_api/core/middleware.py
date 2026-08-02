import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from medical_api.core.request_context import bind_request_context, reset_request_context


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Populates the contextvars in `request_context.py` for the duration of
    each request, so `AuditService` can attribute audit events to the
    request that caused them without every route handler having to pass
    `Request` down through its service/repository call chain.

    Also binds `request_id` into structlog's own contextvars
    (`core/logging.py`'s processor chain starts with
    `structlog.contextvars.merge_contextvars`), so every log line emitted
    anywhere during this request — router, service, repository, at any
    call depth — carries the same `request_id` with no extra plumbing at
    each call site. That's what makes it possible to grep one request's
    full log trail out of the JSON logs.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        tokens = bind_request_context(
            request_id=request_id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        structlog.contextvars.bind_contextvars(request_id=request_id)
        try:
            response = await call_next(request)
        finally:
            reset_request_context(tokens)
            structlog.contextvars.clear_contextvars()
        response.headers["X-Request-Id"] = request_id
        return response
