import time
import uuid
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("DocMind.Access")

class ObservabilityAndSecurityMiddleware(BaseHTTPMiddleware):
    """
    Middleware applying:
    1. Request correlation ID (X-Request-ID) for end-to-end tracing.
    2. HTTP Security Headers (OWASP Top 10 hardening).
    3. Structured latency and status code access logging.
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.perf_counter()
        
        # 1. Correlation ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        # 2. Process request
        response: Response = await call_next(request)

        # 3. Calculate latency
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        
        # 4. Attach Security Headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # 5. Access Log
        logger.info(
            f"req_id={request_id} method={request.method} path={request.url.path} "
            f"status={response.status_code} duration_ms={duration_ms}"
        )

        return response
