"""Auth Service – RS256 JWT + bcrypt password hashing."""
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

import bcrypt
import jwt
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.models import RefreshToken, User
from app.schemas.auth import LoginResponse, RegisterRequest, UserUpdateRequest


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def _load_private_key():
    try:
        with open(settings.PRIVATE_KEY_PATH, "r") as f:
            return f.read()
    except FileNotFoundError:
        # Fallback to symmetric for dev (HS256)
        return settings.SECRET_KEY


def _load_public_key():
    try:
        with open(settings.PUBLIC_KEY_PATH, "r") as f:
            return f.read()
    except FileNotFoundError:
        return settings.SECRET_KEY


def create_access_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp()),
        "type": "access",
    }
    key = _load_private_key()
    algorithm = settings.ALGORITHM if key != settings.SECRET_KEY else "HS256"
    return jwt.encode(payload, key, algorithm=algorithm)


def create_refresh_token_value() -> str:
    return secrets.token_urlsafe(64)


def decode_token(token: str) -> dict:
    key = _load_public_key()
    algorithm = settings.ALGORITHM if key != settings.SECRET_KEY else "HS256"
    try:
        return jwt.decode(token, key, algorithms=[algorithm])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token.")


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, body: RegisterRequest) -> User:
        # Check if email already registered
        result = await self.db.execute(select(User).where(User.email == body.email))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Email already registered.")

        user = User(
            email=body.email,
            hashed_password=hash_password(body.password),
            full_name=body.full_name,
            phone=body.phone,
            preferred_language=body.preferred_language,
            role="student",
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def login(self, email: str, password: str) -> LoginResponse:
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(status_code=403, detail="Account is deactivated.")

        # Update last login
        user.last_login = datetime.now(timezone.utc)

        # Create refresh token
        refresh_val = create_refresh_token_value()
        refresh_token = RefreshToken(
            user_id=user.id,
            token=refresh_val,
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
        self.db.add(refresh_token)
        await self.db.commit()

        return LoginResponse(
            access_token=create_access_token(user),
            refresh_token=refresh_val,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def refresh(self, refresh_token_value: str) -> LoginResponse:
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.token == refresh_token_value,
                RefreshToken.is_revoked == False,
            )
        )
        token_obj = result.scalar_one_or_none()

        if not token_obj:
            raise HTTPException(status_code=401, detail="Invalid refresh token.")
        if token_obj.expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=401, detail="Refresh token expired.")

        user = await self.db.get(User, token_obj.user_id)
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="User not found or inactive.")

        # Rotate refresh token
        token_obj.is_revoked = True
        new_refresh_val = create_refresh_token_value()
        new_token = RefreshToken(
            user_id=user.id,
            token=new_refresh_val,
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
        self.db.add(new_token)
        await self.db.commit()

        return LoginResponse(
            access_token=create_access_token(user),
            refresh_token=new_refresh_val,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def logout(self, refresh_token_value: str):
        result = await self.db.execute(
            select(RefreshToken).where(RefreshToken.token == refresh_token_value)
        )
        token_obj = result.scalar_one_or_none()
        if token_obj:
            token_obj.is_revoked = True
            await self.db.commit()

    async def get_current_user(self, token: str) -> User:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload.")

        user = await self.db.get(User, user_id)
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="User not found or inactive.")
        return user

    async def update_profile(self, user_id: UUID, body: UserUpdateRequest) -> User:
        user = await self.db.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")

        if body.full_name is not None:
            user.full_name = body.full_name
        if body.phone is not None:
            user.phone = body.phone
        if body.preferred_language is not None:
            user.preferred_language = body.preferred_language

        # Merge profile_data fields
        profile = user.profile_data or {}
        convenience_fields = {
            "community": body.community,
            "annual_income": body.annual_income,
            "course": body.course,
            "study_level": body.study_level,
            "gender": body.gender,
            "grade_percentage": body.grade_percentage,
            "college_name": body.college_name,
            "district": body.district,
        }
        for key, val in convenience_fields.items():
            if val is not None:
                profile[key] = val

        if body.profile_data:
            profile.update(body.profile_data)

        user.profile_data = profile
        await self.db.commit()
        await self.db.refresh(user)
        return user
