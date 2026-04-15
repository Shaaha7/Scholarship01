"""
Admin Endpoints
================
POST /admin/scholarships        – Create scholarship
PUT  /admin/scholarships/{id}   – Update scholarship
DELETE /admin/scholarships/{id} – Delete scholarship
POST /admin/upload              – Upload & ingest scholarship PDF
GET  /admin/stats               – Dashboard stats
GET  /admin/users               – List users
"""
import os
import tempfile
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user, require_admin
from app.db.session import get_db
from app.models.models import Application, Scholarship, User
from app.schemas.admin import AdminStatsResponse, CreateScholarshipRequest, UpdateScholarshipRequest
from app.schemas.scholarship import ScholarshipDetailResponse
from app.schemas.auth import UserResponse
from app.services.ingestion_service import IngestionService
from app.services.scholarship_service import ScholarshipService

router = APIRouter()


@router.get("/stats", response_model=AdminStatsResponse)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    """Get platform-wide statistics for admin dashboard."""
    total_scholarships = await db.scalar(select(func.count(Scholarship.id)))
    active_scholarships = await db.scalar(
        select(func.count(Scholarship.id)).where(Scholarship.is_active == True)
    )
    total_users = await db.scalar(select(func.count(User.id)))
    total_applications = await db.scalar(select(func.count(Application.id)))

    # Category breakdown
    cat_result = await db.execute(
        select(Scholarship.category, func.count(Scholarship.id))
        .group_by(Scholarship.category)
    )
    category_breakdown = {row[0]: row[1] for row in cat_result}

    return AdminStatsResponse(
        total_scholarships=total_scholarships or 0,
        active_scholarships=active_scholarships or 0,
        total_users=total_users or 0,
        total_applications=total_applications or 0,
        category_breakdown=category_breakdown,
    )


@router.post("/scholarships", response_model=ScholarshipDetailResponse, status_code=201)
async def create_scholarship(
    body: CreateScholarshipRequest,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    """Create a new scholarship entry."""
    svc = ScholarshipService(db)
    return await svc.create_scholarship(body)


@router.put("/scholarships/{scholarship_id}", response_model=ScholarshipDetailResponse)
async def update_scholarship(
    scholarship_id: UUID,
    body: UpdateScholarshipRequest,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    """Update an existing scholarship."""
    svc = ScholarshipService(db)
    return await svc.update_scholarship(scholarship_id, body)


@router.delete("/scholarships/{scholarship_id}", status_code=204)
async def delete_scholarship(
    scholarship_id: UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    """Soft-delete a scholarship."""
    svc = ScholarshipService(db)
    await svc.soft_delete(scholarship_id)


@router.post("/upload")
async def upload_scholarship_pdf(
    file: UploadFile = File(..., description="Scholarship PDF document"),
    scholarship_title: str = Form(...),
    provider: str = Form(...),
    category: str = Form(...),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    """
    Upload a scholarship PDF, parse it, chunk it,
    embed with BGE-M3, and upsert to Pinecone + PostgreSQL.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    if file.size and file.size > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="File too large. Max 10MB.")

    # Save temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        svc = IngestionService(db)
        result = await svc.ingest_pdf(
            pdf_path=tmp_path,
            scholarship_title=scholarship_title,
            provider=provider,
            category=category,
            source_filename=file.filename,
        )
        return {
            "message": "PDF ingested successfully.",
            "scholarship_id": str(result["scholarship_id"]),
            "chunks_created": result["chunks_created"],
            "pinecone_upserted": result["pinecone_upserted"],
        }
    finally:
        os.unlink(tmp_path)


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    role: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    """List all registered users."""
    query = select(User).limit(limit).offset(offset).order_by(User.created_at.desc())
    if role:
        query = query.where(User.role == role)
    result = await db.execute(query)
    users = result.scalars().all()
    return [UserResponse.model_validate(u) for u in users]
