import logging
import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.time()
        request_id = request.headers.get("X-Request-ID", "unknown")

        logger.info(f"[{request_id}] {request.method} {request.url.path} - Starting")

        response = await call_next(request)

        process_time = time.time() - start_time
        logger.info(
            f"[{request_id}] {request.method} {request.url.path} - "
            f"Completed with status {response.status_code} in {process_time:.2f}s"
        )

        response.headers["X-Process-Time"] = str(process_time)
        return response
