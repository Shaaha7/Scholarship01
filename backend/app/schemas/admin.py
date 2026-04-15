"""Pydantic v2 Schemas – Admin"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class AdminStatsResponse(BaseModel):
    total_scholarships: int
    active_scholarships: int
    total_users: int
    total_applications: int
    category_breakdown: Dict[str, int]


class EligibilityMatrixRequest(BaseModel):
    min_annual_income: Optional[float] = None
    max_annual_income: Optional[float] = None
    community_list: Optional[List[str]] = None
    gender_req: str = "any"
    course_type: Optional[List[str]] = None
    min_percentage: Optional[float] = None
    min_age: Optional[int] = None
    max_age: Optional[int] = None
    study_level: Optional[List[str]] = None
    disability_required: bool = False
    first_gen_learner: bool = False
    state_resident_required: bool = True
    min_tn_residence_years: Optional[int] = None


class CreateScholarshipRequest(BaseModel):
    title: str = Field(..., min_length=5, max_length=500)
    title_tamil: Optional[str] = None
    description: str = Field(..., min_length=10)
    description_tamil: Optional[str] = None
    provider: str
    provider_url: Optional[str] = None
    scheme_code: Optional[str] = None
    category: str
    amount: Optional[float] = None
    amount_description: Optional[str] = None
    deadline: Optional[datetime] = None
    academic_year: Optional[str] = None
    application_url: Optional[str] = None
    is_renewable: bool = False
    eligibility: Optional[EligibilityMatrixRequest] = None


class UpdateScholarshipRequest(BaseModel):
    title: Optional[str] = None
    title_tamil: Optional[str] = None
    description: Optional[str] = None
    description_tamil: Optional[str] = None
    provider: Optional[str] = None
    category: Optional[str] = None
    amount: Optional[float] = None
    deadline: Optional[datetime] = None
    application_url: Optional[str] = None
    is_active: Optional[bool] = None
    eligibility: Optional[EligibilityMatrixRequest] = None
