import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from medical_api.core.request_context import bind_request_context, reset_request_context


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Populates the contextvars in `request_context.py` for the duration of
    each request, so `AuditService` can attribute audit events to the
    request that caused them without every route handler having to pass
    `Request` down through its service/repository call chain.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        tokens = bind_request_context(
            request_id=request_id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        try:
            response = await call_next(request)
        finally:
            reset_request_context(tokens)
        response.headers["X-Request-Id"] = request_id
        return response
