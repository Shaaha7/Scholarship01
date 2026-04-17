"""
TamilScholar Pro – FastAPI Application Entry Point
==================================================
Production-ready FastAPI app with:
- RS256 JWT authentication
- SlowAPI rate limiting
- Prompt Guard middleware
- CORS configuration
- Startup database initialization
- Sentry error tracking
- Redis caching
"""
import logging
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.api.v1.router import api_router
from app.core.config import settings
from app.db.session import create_tables
from app.middleware.prompt_guard import PromptGuardMiddleware
from app.middleware.security import SecurityHeadersMiddleware
from app.middleware.csrf import CSRFMiddleware
from app.services.redis_service import redis_service
from app.utils.logging_config import get_logger

# ── Sentry Integration ─────────────────────────────────────────────────────────
if settings.ENVIRONMENT == "production":
    sentry_sdk.init(
        dsn=getattr(settings, 'SENTRY_DSN', None),
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
        environment=settings.ENVIRONMENT,
        release=settings.APP_VERSION,
    )

# ── Structured Logging ─────────────────────────────────────────────────────────
logger = get_logger(__name__)

# ── Rate Limiter ──────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["200/hour"])


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    # Connect to Redis
    await redis_service.connect()

    # Create database tables
    if settings.ENVIRONMENT == "development":
        await create_tables()
        logger.info("✅ Database tables initialized")

    # Seed initial admin user
    await seed_admin()

    yield

    # Disconnect Redis
    await redis_service.disconnect()
    logger.info("🛑 Shutting down TamilScholar Pro")


async def seed_admin():
    """Create the first admin user if not exists."""
    try:
        from app.db.session import AsyncSessionLocal
        from app.models.models import User
        from app.services.auth_service import hash_password
        from sqlalchemy import select

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(User).where(User.email == settings.FIRST_ADMIN_EMAIL)
            )
            existing = result.scalar_one_or_none()
            if not existing:
                admin = User(
                    email=settings.FIRST_ADMIN_EMAIL,
                    hashed_password=hash_password(settings.FIRST_ADMIN_PASSWORD),
                    full_name="System Administrator",
                    role="admin",
                    is_active=True,
                    is_verified=True,
                )
                session.add(admin)
                await session.commit()
                logger.info(f"✅ Admin user created: {settings.FIRST_ADMIN_EMAIL}")
    except Exception as e:
        logger.warning(f"Admin seed skipped: {e}")


# ── FastAPI App ────────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
## TamilScholar Pro API

AI-powered multilingual scholarship discovery engine for Tamil Nadu students.

### Features
- 🔐 RS256 JWT Authentication
- 🤖 LangGraph AI Agent (Tamil/English/Tanglish)
- 🔍 Hybrid Search (PostgreSQL + Pinecone)
- 📚 BGE-M3 Multilingual Embeddings
- ⚡ Groq Llama 3 70B Inference
- 🛡️ Rate Limiting + Prompt Guard
    """,
    docs_url="/docs",
    openapi_url="/openapi.json",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── State ─────────────────────────────────────────────────────────────────────
app.state.limiter = limiter

# ── Middleware Stack (order matters: last added = first executed) ──────────────

# 1. Security Headers
app.add_middleware(SecurityHeadersMiddleware)

# 2. CSRF Protection
if settings.ENVIRONMENT == "production":
    app.add_middleware(CSRFMiddleware)

# 3. Prompt Guard (blocks jailbreaks before they hit endpoints)
app.add_middleware(PromptGuardMiddleware)

# 3. Trusted Hosts
if settings.ENVIRONMENT == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["tamilscholar.gov.in", "*.tamilscholar.gov.in", "*.vercel.app"],
    )

# 4. CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept-Language", "X-Session-ID"],
    expose_headers=["X-Rate-Limit-Remaining", "X-Rate-Limit-Reset"],
)

# 5. SlowAPI Rate Limiting
app.add_middleware(SlowAPIMiddleware)

# ── Exception Handlers ────────────────────────────────────────────────────────
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal server error occurred.",
            "type": "internal_error",
        },
    )


# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(api_router, prefix="/api/v1")


# ── Health Check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for load balancers."""
    health_status = {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "dependencies": {},
    }
    
    # Check Redis
    try:
        redis_stats = await redis_service.get_stats()
        health_status["dependencies"]["redis"] = {
            "status": "healthy" if redis_stats.get("connected") else "unhealthy",
            "details": redis_stats,
        }
    except Exception as e:
        health_status["dependencies"]["redis"] = {
            "status": "unhealthy",
            "error": str(e),
        }
    
    # Check Database
    try:
        from app.db.session import engine
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        health_status["dependencies"]["database"] = {
            "status": "healthy",
        }
    except Exception as e:
        health_status["dependencies"]["database"] = {
            "status": "unhealthy",
            "error": str(e),
        }
        health_status["status"] = "degraded"
    
    # Check Pinecone
    try:
        from app.services.pinecone_service import pinecone_service
        pinecone_stats = await pinecone_service.get_stats()
        health_status["dependencies"]["pinecone"] = {
            "status": "healthy" if pinecone_stats.get("connected") else "unhealthy",
            "details": pinecone_stats,
        }
    except Exception as e:
        health_status["dependencies"]["pinecone"] = {
            "status": "unhealthy",
            "error": str(e),
        }
    
    return health_status


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": f"Welcome to {settings.APP_NAME} API",
        "docs": "/api/v1/docs",
        "version": settings.APP_VERSION,
    }
