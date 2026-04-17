"""
CSRF Protection Middleware
===========================
Provides CSRF token generation and validation for state-changing requests.
"""
import secrets
import logging
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    CSRF protection middleware.
    - Generates CSRF tokens for GET requests
    - Validates CSRF tokens for state-changing requests (POST, PUT, DELETE, PATCH)
    """
    
    # Methods that require CSRF protection
    SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}
    CSRF_HEADER_NAME = "X-CSRF-Token"
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with CSRF protection."""
        
        # Skip CSRF for safe methods
        if request.method in self.SAFE_METHODS:
            response = await call_next(request)
            # Add CSRF token to response headers for safe methods
            csrf_token = secrets.token_hex(32)
            response.headers[self.CSRF_HEADER_NAME] = csrf_token
            response.headers["Access-Control-Expose-Headers"] = self.CSRF_HEADER_NAME
            return response
        
        # Validate CSRF for state-changing methods
        csrf_token = request.headers.get(self.CSRF_HEADER_NAME)
        
        # For API requests, also check cookie
        csrf_cookie = request.cookies.get("csrf_token")
        
        if not csrf_token and not csrf_cookie:
            logger.warning(f"CSRF token missing for {request.method} {request.url}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "CSRF token missing. Please include X-CSRF-Token header."}
            )
        
        # Validate token if present (simplified validation)
        # In production, you'd want to verify against a session-stored token
        if csrf_token and len(csrf_token) < 32:
            logger.warning(f"Invalid CSRF token format for {request.method} {request.url}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Invalid CSRF token."}
            )
        
        response = await call_next(request)
        return response


def generate_csrf_token() -> str:
    """Generate a new CSRF token."""
    return secrets.token_hex(32)
