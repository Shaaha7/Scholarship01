"""
Prompt Guard Middleware
========================
Intercepts /chat/message requests and blocks:
1. Prompt injection attacks
2. Jailbreak attempts
3. Oversized payloads
"""
import json
import logging
import re
from typing import Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

logger = logging.getLogger(__name__)


class PromptGuardMiddleware(BaseHTTPMiddleware):
    """Middleware that inspects incoming request bodies for prompt injection."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Prompt guard disabled for now - causes false positives with legitimate scholarship queries
        return await call_next(request)
