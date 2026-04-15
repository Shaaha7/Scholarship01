"""Scholarship Service – SQL queries + hybrid search orchestration."""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.models import Application, EligibilityMatrix, Scholarship
from app.schemas.admin import CreateScholarshipRequest, UpdateScholarshipRequest


class ScholarshipService:
    def __init__(self, db: AsyncSession = None):
        self.db = db

    async def filter_by_hard_constraints(
        self,
        category: Optional[str] = None,
        max_income: Optional[float] = None,
        gender_req: Optional[str] = None,
        course_type: Optional[str] = None,
        study_level: Optional[str] = None,
        min_percentage: Optional[float] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Phase A: SQL hard-constraint pre-filter."""
        query = (
            select(Scholarship)
            .options(selectinload(Scholarship.eligibility))
            .where(Scholarship.is_active == True)
        )

        if category:
            query = query.where(Scholarship.category == category)

        # Join eligibility for income/gender/course filters
        if max_income or gender_req or course_type or study_level or min_percentage:
            query = query.join(EligibilityMatrix, EligibilityMatrix.scholarship_id == Scholarship.id, isouter=True)

            if max_income:
                query = query.where(
                    or_(
                        EligibilityMatrix.max_annual_income == None,
                        EligibilityMatrix.max_annual_income >= max_income,
                    )
                )

            if gender_req and gender_req != "any":
                query = query.where(
                    or_(
                        EligibilityMatrix.gender_req == "any",
                        EligibilityMatrix.gender_req == gender_req,
                    )
                )

        # Prefer scholarships with earlier deadlines (and avoid random ordering).
        query = query.order_by(Scholarship.deadline.asc().nullslast()).limit(limit)
        result = await self.db.execute(query)
        scholarships = result.scalars().unique().all()

        return [self._to_dict(s) for s in scholarships]

    def _to_dict(self, s: Scholarship) -> Dict[str, Any]:
        return {
            "id": s.id,
            "title": s.title,
            "title_tamil": s.title_tamil,
            "description": s.description,
            "description_tamil": s.description_tamil,
            "provider": s.provider,
            "provider_url": s.provider_url,
            "scheme_code": s.scheme_code,
            "category": s.category,
            "amount": s.amount,
            "amount_description": s.amount_description,
            "deadline": s.deadline,
            "academic_year": s.academic_year,
            "application_url": s.application_url,
            "is_active": s.is_active,
            "is_renewable": s.is_renewable,
            "eligibility": {
                "min_annual_income": s.eligibility.min_annual_income if s.eligibility else None,
                "max_annual_income": s.eligibility.max_annual_income if s.eligibility else None,
                "community_list": s.eligibility.community_list if s.eligibility else [],
                "gender_req": s.eligibility.gender_req if s.eligibility else "any",
                "course_type": s.eligibility.course_type if s.eligibility else [],
                "study_level": s.eligibility.study_level if s.eligibility else [],
                "min_percentage": s.eligibility.min_percentage if s.eligibility else None,
                "disability_required": s.eligibility.disability_required if s.eligibility else False,
                "first_gen_learner": s.eligibility.first_gen_learner if s.eligibility else False,
                "state_resident_required": s.eligibility.state_resident_required if s.eligibility else True,
                "min_age": s.eligibility.min_age if s.eligibility else None,
                "max_age": s.eligibility.max_age if s.eligibility else None,
            } if s.eligibility else None,
            "created_at": s.created_at,
            "semantic_score": None,
            "final_score": None,
        }

    async def hybrid_search(
        self,
        query: str,
        category: Optional[str] = None,
        max_income: Optional[float] = None,
        gender_req: Optional[str] = None,
        course_type: Optional[str] = None,
        study_level: Optional[str] = None,
        deadline_within_days: Optional[int] = None,
        limit: int = 10,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Full hybrid search combining SQL + vector similarity."""
        from app.services.embedding_service import EmbeddingService
        from app.services.pinecone_service import PineconeService

        # SQL pre-filter
        candidates = await self.filter_by_hard_constraints(
            category=category,
            max_income=max_income,
            gender_req=gender_req,
            course_type=course_type,
            study_level=study_level,
            limit=100,
        )

        if deadline_within_days:
            cutoff = datetime.now(timezone.utc) + timedelta(days=deadline_within_days)
            candidates = [c for c in candidates if c.get("deadline") and c["deadline"] <= cutoff]

        if not candidates:
            return []

        # Semantic re-ranking
        try:
            emb_svc = EmbeddingService()
            pinecone_svc = PineconeService()
            query_emb = await emb_svc.embed_query(query)
            candidate_ids = [str(c["id"]) for c in candidates]
            pinecone_results = await pinecone_svc.semantic_search(query_emb, candidate_ids, top_k=limit + offset)
            score_map = {r["scholarship_id"]: r["score"] for r in pinecone_results}

            for c in candidates:
                c["semantic_score"] = score_map.get(str(c["id"]), 0.0)
                c["final_score"] = c["semantic_score"]

            candidates.sort(key=lambda x: x["final_score"], reverse=True)
        except Exception:
            pass  # Fall back to SQL ordering if vector search fails

        return candidates[offset: offset + limit]

    async def list_scholarships(
        self,
        category: Optional[str] = None,
        is_active: bool = True,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[Dict], int]:
        query = (
            select(Scholarship)
            .options(selectinload(Scholarship.eligibility))
            .where(Scholarship.is_active == is_active)
            .order_by(Scholarship.deadline.asc().nullslast())
            .limit(limit)
            .offset(offset)
        )
        if category:
            query = query.where(Scholarship.category == category)

        from sqlalchemy import func
        count_query = select(func.count(Scholarship.id)).where(Scholarship.is_active == is_active)
        if category:
            count_query = count_query.where(Scholarship.category == category)

        result = await self.db.execute(query)
        total = await self.db.scalar(count_query)
        scholarships = result.scalars().unique().all()
        return [self._to_dict(s) for s in scholarships], total or 0

    async def get_by_id(self, scholarship_id: UUID) -> Dict[str, Any]:
        result = await self.db.execute(
            select(Scholarship)
            .options(selectinload(Scholarship.eligibility))
            .where(Scholarship.id == scholarship_id)
        )
        s = result.scalar_one_or_none()
        if not s:
            raise HTTPException(status_code=404, detail="Scholarship not found.")
        return self._to_dict(s)

    async def get_upcoming_deadlines(self, days: int = 30, category: Optional[str] = None):
        cutoff = datetime.now(timezone.utc) + timedelta(days=days)
        query = (
            select(Scholarship)
            .options(selectinload(Scholarship.eligibility))
            .where(
                Scholarship.is_active == True,
                Scholarship.deadline != None,
                Scholarship.deadline <= cutoff,
                Scholarship.deadline >= datetime.now(timezone.utc),
            )
            .order_by(Scholarship.deadline.asc())
        )
        if category:
            query = query.where(Scholarship.category == category)
        result = await self.db.execute(query)
        return [self._to_dict(s) for s in result.scalars().all()]

    async def save_for_user(self, user_id: UUID, scholarship_id: UUID) -> Application:
        # Check scholarship exists
        s = await self.db.get(Scholarship, scholarship_id)
        if not s:
            raise HTTPException(status_code=404, detail="Scholarship not found.")

        # Check not already saved
        result = await self.db.execute(
            select(Application).where(
                Application.user_id == user_id,
                Application.scholarship_id == scholarship_id,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        app = Application(user_id=user_id, scholarship_id=scholarship_id, status="saved")
        self.db.add(app)
        await self.db.commit()
        await self.db.refresh(app)
        return app

    async def create_scholarship(self, body: CreateScholarshipRequest) -> Dict[str, Any]:
        from app.models.models import EligibilityMatrix
        s = Scholarship(
            title=body.title,
            title_tamil=body.title_tamil,
            description=body.description,
            description_tamil=body.description_tamil,
            provider=body.provider,
            provider_url=body.provider_url,
            scheme_code=body.scheme_code,
            category=body.category,
            amount=body.amount,
            amount_description=body.amount_description,
            deadline=body.deadline,
            academic_year=body.academic_year,
            application_url=body.application_url,
            is_renewable=body.is_renewable,
        )
        self.db.add(s)
        await self.db.flush()

        if body.eligibility:
            em = EligibilityMatrix(scholarship_id=s.id, **body.eligibility.model_dump())
            self.db.add(em)

        await self.db.commit()
        await self.db.refresh(s)
        return self._to_dict(s)

    async def update_scholarship(self, scholarship_id: UUID, body: UpdateScholarshipRequest) -> Dict[str, Any]:
        s = await self.db.get(Scholarship, scholarship_id)
        if not s:
            raise HTTPException(status_code=404, detail="Scholarship not found.")

        for field, val in body.model_dump(exclude_none=True, exclude={"eligibility"}).items():
            setattr(s, field, val)

        if body.eligibility:
            em = await self.db.get(EligibilityMatrix, s.id)
            if em:
                for field, val in body.eligibility.model_dump(exclude_none=True).items():
                    setattr(em, field, val)

        await self.db.commit()
        await self.db.refresh(s)
        return self._to_dict(s)

    async def soft_delete(self, scholarship_id: UUID):
        s = await self.db.get(Scholarship, scholarship_id)
        if not s:
            raise HTTPException(status_code=404, detail="Scholarship not found.")
        s.is_active = False
        await self.db.commit()
