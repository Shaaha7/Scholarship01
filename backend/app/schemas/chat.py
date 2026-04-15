"""Pydantic v2 Schemas – Chat"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class ChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = None  # Resume existing session


class ChatMessageResponse(BaseModel):
    session_id: str
    response: str
    language: str
    intent: str
    scholarships: List[Dict[str, Any]] = []
    sources: List[str] = []
    extra_metadata: Dict[str, Any] = {}


class ChatMessageHistoryItem(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    role: str
    content: str
    language: Optional[str]
    created_at: datetime


class ChatSessionResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    session_token: str
    detected_language: Optional[str]
    created_at: datetime
    updated_at: datetime
