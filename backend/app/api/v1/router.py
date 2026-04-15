"""API v1 Router – aggregates all endpoint routers."""
from fastapi import APIRouter

from app.api.v1.endpoints import auth, scholarships, chat, admin, reminders

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(scholarships.router, prefix="/scholarships", tags=["Scholarships"])
api_router.include_router(chat.router, prefix="/chat", tags=["AI Chat"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
api_router.include_router(reminders.router, prefix="/reminders", tags=["Reminders"])
