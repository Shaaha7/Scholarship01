"""
Scholarship Endpoints
======================
GET  /scholarships/search  – Hybrid search
GET  /scholarships/        – List with filters
GET  /scholarships/{id}    – Get scholarship detail
POST /scholarships/{id}/save – Save to user's list
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.schemas.scholarship import ScholarshipListResponse, ScholarshipSearchRequest, ScholarshipDetailResponse
from app.services.scholarship_service import ScholarshipService

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get("/search", response_model=List[ScholarshipDetailResponse])
@limiter.limit(settings.RATE_LIMIT_SEARCH)
async def search_scholarships(
    request: Request,
    q: str = Query(..., min_length=1, max_length=500, description="Search query (Tamil/English/Tanglish)"),
    category: Optional[str] = Query(None, description="Community: BC, MBC, SC, ST, General, OBC, EWS"),
    max_income: Optional[float] = Query(None, description="Max annual family income in INR"),
    gender: Optional[str] = Query(None, description="Gender: any, female, male"),
    course_type: Optional[str] = Query(None),
    study_level: Optional[str] = Query(None, description="UG, PG, PhD, Diploma, School"),
    deadline_within_days: Optional[int] = Query(None, description="Show only scholarships with deadline within N days"),
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    Hybrid scholarship search combining:
    - SQL hard constraint filtering (income, community, gender)
    - Semantic similarity via Pinecone vector search
    """
    svc = ScholarshipService(db)
    results = await svc.hybrid_search(
        query=q,
        category=category,
        max_income=max_income,
        gender_req=gender,
        course_type=course_type,
        study_level=study_level,
        deadline_within_days=deadline_within_days,
        limit=limit,
        offset=offset,
    )
    return results


@router.get("", response_model=ScholarshipListResponse)
@router.get("/", response_model=ScholarshipListResponse)
async def list_scholarships(
    category: Optional[str] = Query(None),
    is_active: bool = Query(True),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List all scholarships with optional filters."""
    svc = ScholarshipService(db)
    items, total = await svc.list_scholarships(
        category=category,
        is_active=is_active,
        limit=limit,
        offset=offset,
    )
    return ScholarshipListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{scholarship_id}", response_model=ScholarshipDetailResponse)
async def get_scholarship(
    scholarship_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get full details of a specific scholarship."""
    svc = ScholarshipService(db)
    scholarship = await svc.get_by_id(scholarship_id)
    return scholarship


@router.post("/{scholarship_id}/save", status_code=status.HTTP_201_CREATED)
async def save_scholarship(
    scholarship_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Save a scholarship to user's application list."""
    svc = ScholarshipService(db)
    application = await svc.save_for_user(
        user_id=current_user.id,
        scholarship_id=scholarship_id,
    )
    return {"message": "Scholarship saved successfully.", "application_id": str(application.id)}


@router.get("/upcoming/deadlines", response_model=List[ScholarshipDetailResponse])
async def upcoming_deadlines(
    days: int = Query(30, ge=1, le=90, description="Scholarships with deadlines within N days"),
    category: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get scholarships with upcoming deadlines."""
    svc = ScholarshipService(db)
    return await svc.get_upcoming_deadlines(days=days, category=category)
