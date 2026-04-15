"""Pydantic v2 Schemas – Scholarships"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, HttpUrl


class EligibilityMatrixResponse(BaseModel):
    model_config = {"from_attributes": True}
    min_annual_income: Optional[float]
    max_annual_income: Optional[float]
    community_list: Optional[List[str]]
    gender_req: str
    course_type: Optional[List[str]]
    min_percentage: Optional[float]
    min_age: Optional[int]
    max_age: Optional[int]
    study_level: Optional[List[str]]
    disability_required: bool
    first_gen_learner: bool
    state_resident_required: bool


class ScholarshipDetailResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    title: str
    title_tamil: Optional[str]
    description: str
    description_tamil: Optional[str]
    provider: str
    provider_url: Optional[str]
    scheme_code: Optional[str]
    category: str
    amount: Optional[float]
    amount_description: Optional[str]
    deadline: Optional[datetime]
    academic_year: Optional[str]
    application_url: Optional[str]
    is_active: bool
    is_renewable: bool
    eligibility: Optional[EligibilityMatrixResponse]
    created_at: datetime
    # Runtime fields (from hybrid search)
    semantic_score: Optional[float] = None
    final_score: Optional[float] = None


class ScholarshipListResponse(BaseModel):
    items: List[ScholarshipDetailResponse]
    total: int
    limit: int
    offset: int


class ScholarshipSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    category: Optional[str] = None
    max_income: Optional[float] = None
    gender_req: Optional[str] = None
    course_type: Optional[str] = None
    study_level: Optional[str] = None
    deadline_within_days: Optional[int] = None
    limit: int = Field(default=10, ge=1, le=50)
    offset: int = Field(default=0, ge=0)
