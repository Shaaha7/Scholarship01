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
from app.services.oauth_service import oauth_service

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


# ── OAuth 2.0 Endpoints ───────────────────────────────────────────────────────────
@router.get("/google/url")
async def get_google_auth_url():
    """Get Google OAuth authorization URL."""
    url = oauth_service.get_google_auth_url()
    if not url:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Google OAuth not configured"
        )
    return {"auth_url": url}


@router.post("/google/callback", response_model=LoginResponse)
async def google_oauth_callback(
    code: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Handle Google OAuth callback.
    Exchange code for tokens, get user info, and create/login user.
    """
    try:
        # Exchange code for tokens
        tokens = await oauth_service.exchange_code_for_tokens(code)
        
        # Get user info from Google
        user_info = await oauth_service.get_google_user_info(tokens["access_token"])
        
        # Check if user exists by email
        auth_service = AuthService(db)
        from app.models.models import User
        from sqlalchemy import select
        
        result = await db.execute(
            select(User).where(User.email == user_info["email"])
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            # Login existing user
            login_response = await auth_service.login(
                existing_user.email,
                password=None,  # OAuth users don't need password
                oauth_provider="google",
                oauth_id=user_info["id"]
            )
        else:
            # Create new user
            register_data = RegisterRequest(
                email=user_info["email"],
                password=None,  # Will be set to random for OAuth users
                full_name=user_info.get("name", ""),
                oauth_provider="google",
                oauth_id=user_info["id"]
            )
            user = await auth_service.register_oauth(register_data)
            login_response = await auth_service.login(
                user.email,
                password=None,
                oauth_provider="google",
                oauth_id=user_info["id"]
            )
        
        return login_response
        
    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth authentication failed: {str(e)}"
        )
