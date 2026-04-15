"""
Authentication Endpoints – RS256 JWT
=====================================
POST /auth/register
POST /auth/login
POST /auth/refresh
POST /auth/logout
GET  /auth/me
PUT  /auth/me
"""
from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.schemas.auth import (
    LoginRequest, LoginResponse, RefreshRequest,
    RegisterRequest, TokenPayload, UserResponse, UserUpdateRequest,
)
from app.services.auth_service import AuthService

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
security = HTTPBearer()


# ── Dependency: Current User ───────────────────────────────────────────────────
async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: AsyncSession = Depends(get_db),
):
    """Validate JWT and return current user."""
    auth_service = AuthService(db)
    return await auth_service.get_current_user(credentials.credentials)


async def require_admin(current_user=Depends(get_current_user)):
    """Require admin role."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return current_user


# ── Endpoints ─────────────────────────────────────────────────────────────────
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def register(
    request: Request,
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """Register a new student account."""
    auth_service = AuthService(db)
    user = await auth_service.register(body)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=LoginResponse)
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def login(
    request: Request,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Login and receive access + refresh tokens."""
    auth_service = AuthService(db)
    return await auth_service.login(body.email, body.password)


@router.post("/refresh", response_model=LoginResponse)
async def refresh_token(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """Exchange a refresh token for a new access token."""
    auth_service = AuthService(db)
    return await auth_service.refresh(body.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Revoke refresh token (logout)."""
    auth_service = AuthService(db)
    await auth_service.logout(body.refresh_token)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user=Depends(get_current_user)):
    """Get current user's profile."""
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse)
async def update_me(
    body: UserUpdateRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update current user's profile (including community, income, course)."""
    auth_service = AuthService(db)
    updated = await auth_service.update_profile(current_user.id, body)
    return UserResponse.model_validate(updated)
