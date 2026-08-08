import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send

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


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Baseline response headers with no per-app tuning required — unlike a
    Content-Security-Policy (which needs to enumerate each frontend's own
    script/style/connect sources and stays a separate, still-open item; see
    "API and application security hardening" in missing_features.md).
    `Strict-Transport-Security` is production-only: sending it over plain
    HTTP in local dev would make a browser cache an HTTPS-only policy for
    `localhost` that's actively wrong for that environment.
    """

    def __init__(self, app: ASGIApp, *, is_production: bool) -> None:
        super().__init__(app)
        self.is_production = is_production

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if self.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        return response


class BodySizeLimitMiddleware:
    """Rejects a request whose declared `Content-Length` exceeds `max_bytes`
    before any route or dependency starts reading it — plain ASGI rather
    than `BaseHTTPMiddleware` so this runs ahead of body consumption instead
    of after Starlette has already buffered it.

    Only catches requests that declare an honest `Content-Length`; a client
    using chunked transfer-encoding without one could still stream an
    oversized body past this check. Real protection against that requires a
    limit at the reverse proxy/load balancer in front of the app, which is
    infrastructure this repo doesn't own yet — see "Production deployment
    infrastructure" in missing_features.md. This is still real defense in
    depth for the common case (an honest or naively malicious oversized
    request) and costs nothing for every normal request.
    """

    def __init__(self, app: ASGIApp, *, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        content_length = next(
            (value for key, value in scope.get("headers", []) if key == b"content-length"), None
        )
        if content_length is not None and int(content_length) > self.max_bytes:
            response = JSONResponse(
                {"detail": "Request body exceeds the maximum allowed size."}, status_code=413
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)
