"""
SQLAlchemy 2.0 ORM Models – TamilScholar Pro
Normalized schema with pgvector support.
"""
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Float, ForeignKey,
    Index, Integer, String, Text, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector


class Base(DeclarativeBase):
    pass


# ─────────────────────────────────────────────────────────────────────────────
# USERS
# ─────────────────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    role: Mapped[str] = mapped_column(
        Enum("student", "admin", "officer", name="user_role"),
        default="student", nullable=False
    )

    # JSONB for flexible profile data: community, income, course, year, etc.
    profile_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, default=dict)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    preferred_language: Mapped[str] = mapped_column(String(10), default="en")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    applications: Mapped[List["Application"]] = relationship(back_populates="user", lazy="selectin")
    reminders: Mapped[List["Reminder"]] = relationship(back_populates="user", lazy="selectin")
    chat_sessions: Mapped[List["ChatSession"]] = relationship(back_populates="user", lazy="selectin")
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(back_populates="user")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    token: Mapped[str] = mapped_column(String(512), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")


# ─────────────────────────────────────────────────────────────────────────────
# SCHOLARSHIPS
# ─────────────────────────────────────────────────────────────────────────────
class Scholarship(Base):
    __tablename__ = "scholarships"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    title_tamil: Mapped[Optional[str]] = mapped_column(String(500))  # Tamil translation
    description: Mapped[str] = mapped_column(Text, nullable=False)
    description_tamil: Mapped[Optional[str]] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(String(255), nullable=False)  # TN Govt Dept
    provider_url: Mapped[Optional[str]] = mapped_column(String(500))
    scheme_code: Mapped[Optional[str]] = mapped_column(String(100), unique=True)  # Govt scheme ID

    # Category – Tamil Nadu community classification
    category: Mapped[str] = mapped_column(
        Enum("BC", "MBC", "SC", "ST", "General", "OBC", "EWS", "Minority", name="community_category"),
        nullable=False, index=True
    )

    amount: Mapped[Optional[float]] = mapped_column(Float)  # Annual amount in INR
    amount_description: Mapped[Optional[str]] = mapped_column(String(500))

    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True)
    academic_year: Mapped[Optional[str]] = mapped_column(String(20))  # e.g., "2024-25"

    application_url: Mapped[Optional[str]] = mapped_column(String(500))
    source_pdf_url: Mapped[Optional[str]] = mapped_column(String(500))

    # Vector chunk tracking
    pinecone_chunk_ids: Mapped[Optional[List[str]]] = mapped_column(JSONB, default=list)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_renewable: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    eligibility: Mapped[Optional["EligibilityMatrix"]] = relationship(
        back_populates="scholarship", uselist=False, lazy="selectin", cascade="all, delete-orphan"
    )
    applications: Mapped[List["Application"]] = relationship(back_populates="scholarship")
    reminders: Mapped[List["Reminder"]] = relationship(back_populates="scholarship")

    __table_args__ = (
        Index("ix_scholarship_deadline_active", "deadline", "is_active"),
        Index("ix_scholarship_category_active", "category", "is_active"),
    )


class EligibilityMatrix(Base):
    """
    One-to-one with Scholarship.
    Stores hard-constraint filters used for SQL pre-filtering before vector search.
    """
    __tablename__ = "eligibility_matrix"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scholarship_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scholarships.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    # Income constraints
    min_annual_income: Mapped[Optional[float]] = mapped_column(Float)
    max_annual_income: Mapped[Optional[float]] = mapped_column(Float)

    # Community eligibility (list of allowed communities)
    community_list: Mapped[Optional[List[str]]] = mapped_column(JSONB, default=list)

    # Gender requirement
    gender_req: Mapped[str] = mapped_column(
        Enum("any", "female", "male", "transgender", name="gender_req"),
        default="any"
    )

    # Course type eligibility
    course_type: Mapped[Optional[List[str]]] = mapped_column(JSONB, default=list)
    # e.g., ["Engineering", "Medicine", "Arts", "Law", "Polytechnic", "ITI"]

    # Academic performance
    min_percentage: Mapped[Optional[float]] = mapped_column(Float)

    # Age constraints
    min_age: Mapped[Optional[int]] = mapped_column(Integer)
    max_age: Mapped[Optional[int]] = mapped_column(Integer)

    # Study level
    study_level: Mapped[Optional[List[str]]] = mapped_column(JSONB, default=list)
    # e.g., ["UG", "PG", "PhD", "Diploma", "School"]

    # Disability, first-generation learner flags
    disability_required: Mapped[bool] = mapped_column(Boolean, default=False)
    first_gen_learner: Mapped[bool] = mapped_column(Boolean, default=False)

    # State residency
    state_resident_required: Mapped[bool] = mapped_column(Boolean, default=True)
    min_tn_residence_years: Mapped[Optional[int]] = mapped_column(Integer)

    scholarship: Mapped["Scholarship"] = relationship(back_populates="eligibility")

    __table_args__ = (
        Index("ix_eligibility_income", "min_annual_income", "max_annual_income"),
        Index("ix_eligibility_scholarship", "scholarship_id"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# APPLICATIONS
# ─────────────────────────────────────────────────────────────────────────────
class Application(Base):
    """Tracks user-saved / applied scholarships."""
    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    scholarship_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("scholarships.id", ondelete="CASCADE"), index=True)

    status: Mapped[str] = mapped_column(
        Enum("saved", "applied", "under_review", "approved", "rejected", "withdrawn", name="application_status"),
        default="saved", nullable=False
    )

    notes: Mapped[Optional[str]] = mapped_column(Text)
    applied_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="applications")
    scholarship: Mapped["Scholarship"] = relationship(back_populates="applications")

    __table_args__ = (
        UniqueConstraint("user_id", "scholarship_id", name="uq_user_scholarship"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# REMINDERS
# ─────────────────────────────────────────────────────────────────────────────
class Reminder(Base):
    """Deadline reminders with simulated cron notification."""
    __tablename__ = "reminders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    scholarship_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("scholarships.id", ondelete="CASCADE"), index=True)

    remind_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    remind_days_before: Mapped[int] = mapped_column(Integer, default=7)
    channel: Mapped[str] = mapped_column(
        Enum("email", "sms", "push", name="reminder_channel"),
        default="email"
    )

    is_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="reminders")
    scholarship: Mapped["Scholarship"] = relationship(back_populates="reminders")


# ─────────────────────────────────────────────────────────────────────────────
# CHAT SESSIONS
# ─────────────────────────────────────────────────────────────────────────────
class ChatSession(Base):
    """Persistent chat sessions with full conversation history."""
    __tablename__ = "chat_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    session_token: Mapped[str] = mapped_column(String(256), unique=True, index=True)

    # Full conversation history stored as JSONB
    messages: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list)

    detected_language: Mapped[Optional[str]] = mapped_column(String(20))
    user_profile_snapshot: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user: Mapped[Optional["User"]] = relationship(back_populates="chat_sessions")
    messages_rel: Mapped[List["ChatMessage"]] = relationship(back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base):
    """Individual chat messages within a session."""
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True)

    role: Mapped[str] = mapped_column(Enum("user", "assistant", "system", name="message_role"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[Optional[str]] = mapped_column(String(20))

    # Metadata: scholarships surfaced, tokens used, etc.
    extra_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped["ChatSession"] = relationship(back_populates="messages_rel")


# ─────────────────────────────────────────────────────────────────────────────
# DOCUMENT CHUNKS (for tracking ingested PDFs)
# ─────────────────────────────────────────────────────────────────────────────
class DocumentChunk(Base):
    """Tracks raw text chunks ingested into Pinecone."""
    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scholarship_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("scholarships.id", ondelete="SET NULL"))
    pinecone_id: Mapped[str] = mapped_column(String(256), unique=True, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_file: Mapped[Optional[str]] = mapped_column(String(500))
    extra_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Optional: store embedding locally (for small deployments without Pinecone)
    embedding: Mapped[Optional[List[float]]] = mapped_column(JSONB, nullable=True)
