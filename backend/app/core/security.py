import time
import uuid
from typing import Optional, Dict
from fastapi import Request, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_auth = HTTPBearer(auto_error=False)

class RateLimiter:
    """
    In-memory sliding-window token bucket rate limiter per client IP.
    Protects inference endpoints from resource exhaustion and denial-of-wallet.
    """
    def __init__(self, max_requests_per_minute: int = 60):
        self.max_requests = max_requests_per_minute
        self.window_seconds = 60.0
        # {client_ip: [timestamp, ...]}
        self._clients: Dict[str, list] = {}

    def is_allowed(self, client_ip: str) -> bool:
        now = time.time()
        timestamps = self._clients.get(client_ip, [])
        # Prune older than window
        timestamps = [t for t in timestamps if now - t < self.window_seconds]
        if len(timestamps) >= self.max_requests:
            self._clients[client_ip] = timestamps
            return False

        timestamps.append(now)
        self._clients[client_ip] = timestamps
        return True

rate_limiter = RateLimiter(max_requests_per_minute=settings.RATE_LIMIT_PER_MINUTE)

async def verify_auth(
    request: Request,
    api_key: Optional[str] = Security(api_key_header),
    bearer: Optional[HTTPAuthorizationCredentials] = Security(bearer_auth)
) -> str:
    """
    Verifies authentication when API_KEY is set in configuration.
    Extracts tenant_id from header 'X-Tenant-ID' or defaults to 'default'.
    """
    if settings.API_KEY:
        token = api_key or (bearer.credentials if bearer else None)
        if not token or token != settings.API_KEY:
            logger.warning(f"Unauthorized access attempt from {request.client.host if request.client else 'unknown'}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing API authentication credentials.",
                headers={"WWW-Authenticate": "Bearer"}
            )

    # Rate limiting check
    client_ip = request.client.host if request.client else "127.0.0.1"
    if not rate_limiter.is_allowed(client_ip):
        logger.warning(f"Rate limit exceeded for client {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Maximum {settings.RATE_LIMIT_PER_MINUTE} requests per minute."
        )

    # Return validated tenant ID
    tenant_id = request.headers.get("X-Tenant-ID", "default").strip()
    return tenant_id

def sanitize_filename(filename: str) -> str:
    """Removes path traversal components and illegal characters from uploaded filenames."""
    import os
    import re
    base = os.path.basename(filename)
    clean = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', base)
    return clean[:100]
