"""Pydantic v2 Schemas – Reminders"""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class CreateReminderRequest(BaseModel):
    scholarship_id: UUID
    remind_days_before: int = Field(default=7, ge=1, le=60)
    channel: str = Field(default="email", pattern="^(email|sms|push)$")


class ReminderResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    scholarship_id: UUID
    remind_at: datetime
    remind_days_before: int
    channel: str
    is_sent: bool
    created_at: datetime
