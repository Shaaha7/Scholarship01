"""Pydantic v2 Schemas – Auth"""
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, field_validator
import re


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=2, max_length=255)
    phone: Optional[str] = None
    preferred_language: str = Field(default="en", pattern="^(en|ta)$")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one digit.")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain at least one special character.")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class TokenPayload(BaseModel):
    sub: str  # user id
    email: str
    role: str
    exp: int
    iat: int


class UserResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    email: str
    full_name: Optional[str]
    phone: Optional[str]
    role: str
    profile_data: Optional[Dict[str, Any]]
    is_active: bool
    is_verified: bool
    preferred_language: str
    created_at: datetime
    last_login: Optional[datetime]


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    preferred_language: Optional[str] = Field(None, pattern="^(en|ta)$")
    profile_data: Optional[Dict[str, Any]] = None
    # Convenience fields that get merged into profile_data
    community: Optional[str] = Field(None, description="BC, MBC, SC, ST, General, OBC, EWS")
    annual_income: Optional[float] = Field(None, ge=0)
    course: Optional[str] = None
    study_level: Optional[str] = Field(None, description="UG, PG, PhD, Diploma, School")
    gender: Optional[str] = Field(None, pattern="^(male|female|transgender|prefer_not_to_say)$")
    grade_percentage: Optional[float] = Field(None, ge=0, le=100)
    college_name: Optional[str] = None
    district: Optional[str] = None
