"""Application configuration using Pydantic v2 Settings."""
from functools import lru_cache
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── App ───────────────────────────────────────────────────────────────────
    APP_NAME: str = "TamilScholar Pro"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # ── Security ──────────────────────────────────────────────────────────────
    SECRET_KEY: str = "changeme-use-openssl-rand-hex-64"
    ALGORITHM: str = "RS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PRIVATE_KEY_PATH: str = "./keys/private.pem"
    PUBLIC_KEY_PATH: str = "./keys/public.pem"

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://tamilscholar:tamilscholar_secret@localhost:5432/tamilscholar_db"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── AI / LLM ──────────────────────────────────────────────────────────────
    OPENAI_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    LLM_PROVIDER: str = "groq"         # "groq" | "openai"
    LLM_MODEL: str = "llama-3.3-70b-versatile" # Groq Llama 3.3 70B (preferred current model)
    LLM_TEMPERATURE: float = 0.3
    LLM_MAX_TOKENS: int = 2048

    # ── Vector DB (Pinecone Serverless) ───────────────────────────────────────
    PINECONE_API_KEY: Optional[str] = None
    PINECONE_ENVIRONMENT: str = "gcp-starter"
    PINECONE_INDEX_NAME: str = "tamilscholar-scholarships"
    PINECONE_DIMENSION: int = 1024  # BGE-M3 output dim

    # ── Embeddings ────────────────────────────────────────────────────────────
    EMBEDDING_MODEL: str = "BAAI/bge-m3"
    EMBEDDING_DEVICE: str = "cpu"

    # ── Rate Limiting ─────────────────────────────────────────────────────────
    RATE_LIMIT_CHAT: str = "20/minute"
    RATE_LIMIT_SEARCH: str = "60/minute"
    RATE_LIMIT_AUTH: str = "10/minute"

    # ── CORS ──────────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://tamilscholar.vercel.app",
    ]

    # ── Prompt Guard ──────────────────────────────────────────────────────────
    PROMPT_GUARD_ENABLED: bool = True
    MAX_PROMPT_LENGTH: int = 2000

    # ── Admin ─────────────────────────────────────────────────────────────────
    FIRST_ADMIN_EMAIL: str = "admin@tamilscholar.gov.in"
    FIRST_ADMIN_PASSWORD: str = "ChangeMe@123!"

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, v):
        if isinstance(v, str):
            return [o.strip() for o in v.split(",")]
        return v


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
